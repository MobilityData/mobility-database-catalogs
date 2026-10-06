"""
Physical-location analysis and existing-point recommendation.

Pair scoring keeps a broad shared-stop group so records around the same
intersection are not missed. That is useful for discovery, but one group can
contain more than one actual boarding location.

This module splits each broad group into smaller physical-location candidates
before recommending a point. A physical-location candidate can contain only
one record from each operator. It also has to stay coherent: every
cross-operator pair inside the candidate must have shared-stop evidence from
pair scoring and no hard conflict.

The recommended point is always an existing GTFS point. No centroid,
midpoint, snapped point, or synthetic stop is created.

Note: the two-agency BoardingSide recommendation rule lives in
workflow._apply_two_agency_recommendations, which runs after served-shape
context is available.
"""

from math import asin, cos, floor, radians, sin, sqrt
import hashlib
import pandas as pd

issue_threshold_ft = 25.0
earth_radius_ft = 20902260.0

location_candidate_classes = {
    "High-Confidence Shared Stop Candidate",
    "Likely Shared Stop Candidate",
    "Uncertain Shared Stop Candidate",
    "Evidence-Assisted Rescue Candidate",
}

location_class_rank = {
    "High-Confidence Shared Stop Candidate": 4,
    "Likely Shared Stop Candidate": 3,
    "Uncertain Shared Stop Candidate": 2,
    "Evidence-Assisted Rescue Candidate": 1,
}

issue_direct_evidence_classes = {
    "High-Confidence Shared Stop Candidate",
    "Likely Shared Stop Candidate",
    "Evidence-Assisted Rescue Candidate",
}


def _clean(v):
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in {"nan", "none", "null"} else s


def _safe_float(v):
    try:
        return float(v)
    except Exception:
        return None


def _haversine_ft(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * earth_radius_ft * asin(sqrt(a))


def _operator_key(row):
    """Row-level operator key with the same fallback idea as pair scoring."""
    for c in (
        "agency_name",
        "GTFS_agency_id",
        "analysis_name",
        "feed_name",
        "feed_key",
    ):
        value = _clean(row.get(c))
        if value:
            return value.lower()
    return "unresolved"


def _find_agency_column(df):
    for c in ("agency_name", "analysis_name"):
        if c in df.columns:
            return c
    raise RuntimeError("No agency field (agency_name or analysis_name) found for recommendation analysis.")


def _find_stop_id_column(df):
    for c in ("GTFS_stop_id", "stop_id"):
        if c in df.columns:
            return c
    raise RuntimeError("No stop_id field found for recommendation analysis.")


def _find_stop_name_column(df):
    for c in ("GTFS_stop_name", "stop_name"):
        if c in df.columns:
            return c
    raise RuntimeError("No stop_name field found for recommendation analysis.")


def _find_source_key_column(df):
    for c in ("source_key",):
        if c in df.columns:
            return c
    raise RuntimeError("No source-key field found for recommendation analysis.")


def _find_group_id_column(df):
    if "shared_stop_group_id" not in df.columns:
        raise RuntimeError("shared_stop_group_id is required for recommendation analysis.")
    return "shared_stop_group_id"


def _find_coordinate_columns(df):
    if {"GTFS_stop_lat", "GTFS_stop_lon"}.issubset(df.columns):
        return "GTFS_stop_lat", "GTFS_stop_lon"
    if {"stop_lat", "stop_lon"}.issubset(df.columns):
        return "stop_lat", "stop_lon"
    raise RuntimeError("Stop latitude/longitude fields were not found.")


def _build_group_confidence_lookup(groups):
    if groups is None or groups.empty or "shared_stop_group_id" not in groups.columns:
        return {}
    if "group_confidence" not in groups.columns:
        return {}
    return dict(zip(
        groups["shared_stop_group_id"].astype(str),
        groups["group_confidence"].astype(str),
    ))


def _build_pair_lookup(pair_df):
    lookup = {}
    if pair_df is None or pair_df.empty:
        return lookup
    if not {"source_key_a", "source_key_b"}.issubset(pair_df.columns):
        return lookup

    for _, r in pair_df.iterrows():
        a = _clean(r.get("source_key_a"))
        b = _clean(r.get("source_key_b"))
        if a and b and a != b:
            lookup[frozenset((a, b))] = r.to_dict()

    return lookup


def _pair_is_location_candidate(pair):
    if not pair:
        return False
    if _clean(pair.get("shared_stop_conflict_codes")):
        return False
    return _clean(pair.get("shared_stop_classification")) in location_candidate_classes


def _pair_score(pair):
    try:
        return int(float(pair.get("shared_stop_score", 0)))
    except Exception:
        return 0


def _pair_distance(pair):
    d = _safe_float(pair.get("distance_ft"))
    return d if d is not None else 999999.0


def _build_physical_location_id(keys):
    token = "|".join(sorted(keys))
    return "SPL_" + hashlib.sha1(token.encode("utf-8")).hexdigest()[:12]


def _build_physical_locations(group, source_c, pair_lookup):
    """Split a broad shared-stop group into coherent boarding-location candidates."""
    members = {}
    for idx, r in group.iterrows():
        key = _clean(r.get(source_c))
        op = _operator_key(r)
        if key:
            members[key] = {"index": idx, "operator": op}

    edges = []
    for a in members:
        for b in members:
            if a >= b:
                continue
            if members[a]["operator"] == members[b]["operator"]:
                continue

            pair = pair_lookup.get(frozenset((a, b)))
            if not _pair_is_location_candidate(pair):
                continue

            cls = _clean(pair.get("shared_stop_classification"))
            edges.append((
                -location_class_rank.get(cls, 0),
                -_pair_score(pair),
                _pair_distance(pair),
                a,
                b,
            ))

    edges.sort()
    cluster_of = {key: key for key in members}
    clusters = {key: {key} for key in members}

    def can_merge(left_id, right_id):
        left = clusters[left_id]
        right = clusters[right_id]
        left_ops = {members[k]["operator"] for k in left}
        right_ops = {members[k]["operator"] for k in right}

        if left_ops & right_ops:
            return False

        for a in left:
            for b in right:
                if not _pair_is_location_candidate(
                    pair_lookup.get(frozenset((a, b)))
                ):
                    return False

        return True

    for _, _, _, a, b in edges:
        left_id = cluster_of[a]
        right_id = cluster_of[b]

        if left_id == right_id or not can_merge(left_id, right_id):
            continue

        merged = clusters[left_id] | clusters[right_id]
        new_id = min(merged)

        del clusters[left_id]
        del clusters[right_id]
        clusters[new_id] = merged

        for key in merged:
            cluster_of[key] = new_id

    locations = []
    unmatched = []

    for keys in clusters.values():
        operators = {members[k]["operator"] for k in keys if members[k]["operator"]}
        if len(keys) < 2 or len(operators) < 2:
            unmatched.extend(keys)
            continue

        pair_rows = []
        key_list = sorted(keys)
        for i, a in enumerate(key_list):
            for b in key_list[i + 1:]:
                pair = pair_lookup.get(frozenset((a, b)))
                if pair:
                    pair_rows.append(pair)

        all_high = bool(pair_rows) and all(
            _clean(p.get("shared_stop_classification"))
            == "High-Confidence Shared Stop Candidate"
            for p in pair_rows
        )

        locations.append({
            "physical_location_id": _build_physical_location_id(keys),
            "source_keys": key_list,
            "operator_count": len(operators),
            "record_count": len(keys),
            "physical_location_match": (
                "High Confidence" if all_high else "Needs Review"
            ),
            "physical_location_score": (
                min(_pair_score(p) for p in pair_rows) if pair_rows else None
            ),
        })

    return locations, unmatched


def _best_direct_pair_evidence(candidate_key, supporter_keys, pair_lookup):
    rows = []
    for supporter_key in supporter_keys:
        if supporter_key == candidate_key:
            continue

        pair = pair_lookup.get(frozenset((candidate_key, supporter_key)))
        if not pair:
            continue

        classification = _clean(pair.get("shared_stop_classification"))
        qualifies = (
            classification in issue_direct_evidence_classes
            and not _clean(pair.get("shared_stop_conflict_codes"))
        )

        rows.append({
            "supporter_source_key": supporter_key,
            "classification": classification,
            "score": _pair_score(pair),
            "qualifies": qualifies,
            "evidence": _clean(pair.get("shared_stop_evidence")),
            "distance_ft": _safe_float(pair.get("distance_ft")),
            "strong_identity_evidence": _clean(
                pair.get("strong_identity_evidence")
            ),
        })

    if not rows:
        return None, []

    best = sorted(
        rows,
        key=lambda x: (
            0 if x["qualifies"] else 1,
            -x["score"],
            x["distance_ft"] if x["distance_ft"] is not None else 999999,
        ),
    )[0]

    return best, rows


def run_recommendation_issue_analysis(records, groups=None, pair_df=None):
    df = records.copy()

    group_c = _find_group_id_column(df)
    agency_c = _find_agency_column(df)
    stop_id_c = _find_stop_id_column(df)
    stop_name_c = _find_stop_name_column(df)
    source_c = _find_source_key_column(df)
    lat_c, lon_c = _find_coordinate_columns(df)

    defaults = {
        "physical_location_id": "",
        "physical_location_match": "",
        "physical_location_status": "",
        "physical_location_score": "",
        "physical_location_operator_count": "",
        "physical_location_record_count": "",
        "recommendation_status_code": "",
        "recommended_point_flag": "N",
        "recommended_source_key": "",
        "recommended_agency": "",
        "recommended_stop_id": "",
        "recommended_lat": "",
        "recommended_lon": "",
        "recommendation_method": "",
        "recommendation_confidence": "",
        "recommendation_support_operator_count": "",
        "distance_to_recommended_ft": "",
        "over_25ft": "N",
        "likely_incorrect_stop_flag": "N",
        "verification_needed": "",
        "recommendation_review_reason": "",
        "issue_confidence": "",
        "issue_direct_pair_score": "",
        "issue_direct_pair_classification": "",
        "issue_direct_pair_evidence": "",
    }

    for c, default in defaults.items():
        df[c] = default

    group_conf = _build_group_confidence_lookup(groups)
    pair_lookup = _build_pair_lookup(pair_df)

    recommendation_rows = []
    issue_rows = []
    unresolved_rows = []
    suppressed_rows = []
    location_rows = []

    grouped = df[df[group_c].astype(str).str.strip().ne("")].groupby(
        group_c, sort=False
    )

    for gid, broad_group in grouped:
        locations, unmatched = _build_physical_locations(
            broad_group, source_c, pair_lookup
        )

        for source_key in unmatched:
            idx = broad_group[
                broad_group[source_c].astype(str).eq(source_key)
            ].index[0]
            df.at[idx, "physical_location_status"] = (
                "NO_CROSS_OPERATOR_LOCATION_MATCH_SELECTED"
            )
            df.at[idx, "physical_location_match"] = "Needs Review"
            df.at[idx, "recommendation_status_code"] = "NOT_ESTABLISHED"
            df.at[idx, "verification_needed"] = "Y"
            df.at[idx, "recommendation_review_reason"] = (
                "NO_CROSS_OPERATOR_LOCATION_MATCH_SELECTED"
            )

        for loc in locations:
            loc_id = loc["physical_location_id"]
            source_keys = loc["source_keys"]
            g = broad_group[
                broad_group[source_c].astype(str).isin(source_keys)
            ].copy()

            for idx in g.index:
                df.at[idx, "physical_location_id"] = loc_id
                df.at[idx, "physical_location_match"] = loc[
                    "physical_location_match"
                ]
                df.at[idx, "physical_location_status"] = (
                    "MATCHED_CROSS_OPERATOR_LOCATION"
                )
                df.at[idx, "physical_location_score"] = str(
                    loc["physical_location_score"]
                    if loc["physical_location_score"] is not None
                    else ""
                )
                df.at[idx, "physical_location_operator_count"] = str(
                    loc["operator_count"]
                )
                df.at[idx, "physical_location_record_count"] = str(
                    loc["record_count"]
                )

            location_rows.append({
                "shared_stop_group_id": gid,
                **loc,
                "group_confidence": group_conf.get(str(gid), ""),
            })

            valid = []
            for idx in g.index:
                lat = _safe_float(df.at[idx, lat_c])
                lon = _safe_float(df.at[idx, lon_c])
                if lat is not None and lon is not None:
                    valid.append(idx)

            operators = {
                _operator_key(df.loc[idx])
                for idx in valid
                if _operator_key(df.loc[idx]) != "unresolved"
            }
            n_ops = len(operators)

            if len(valid) < 2 or n_ops < 2:
                reason = "INSUFFICIENT_VALID_CROSS_OPERATOR_GEOMETRY"
                for idx in g.index:
                    df.at[idx, "recommendation_status_code"] = "UNRESOLVED"
                    df.at[idx, "verification_needed"] = "Y"
                    df.at[idx, "recommendation_review_reason"] = reason

                unresolved_rows.append({
                    "shared_stop_group_id": gid,
                    "physical_location_id": loc_id,
                    "physical_location_match": loc["physical_location_match"],
                    "group_confidence": group_conf.get(str(gid), ""),
                    "recommendation_review_reason": reason,
                    "operator_count": n_ops,
                    "record_count": len(g),
                    "source_keys": " | ".join(source_keys),
                })
                continue

            coords = {
                idx: (
                    _safe_float(df.at[idx, lat_c]),
                    _safe_float(df.at[idx, lon_c]),
                )
                for idx in valid
            }

            dist = {}
            for i in valid:
                for j in valid:
                    if i == j:
                        dist[(i, j)] = 0.0
                    elif (j, i) in dist:
                        dist[(i, j)] = dist[(j, i)]
                    else:
                        dist[(i, j)] = _haversine_ft(
                            coords[i][0], coords[i][1],
                            coords[j][0], coords[j][1],
                        )

            candidate_info = []
            for candidate_index in valid:
                supporters = [
                    j for j in valid
                    if dist[(candidate_index, j)] <= issue_threshold_ft + 1e-9
                ]
                support_ops = {
                    _operator_key(df.loc[j])
                    for j in supporters
                    if _operator_key(df.loc[j]) != "unresolved"
                }

                candidate_info.append({
                    "candidate_index": candidate_index,
                    "supporters": supporters,
                    "support_ops": support_ops,
                    "support_n": len(support_ops),
                    "max_support_dist": max(
                        dist[(candidate_index, j)] for j in supporters
                    ),
                    "sum_support_dist": sum(
                        dist[(candidate_index, j)] for j in supporters
                    ),
                })

            max_support = max(x["support_n"] for x in candidate_info)
            required_majority = floor(n_ops / 2) + 1
            resolved = False
            method = ""
            recommendation_conf = ""
            reason = ""
            chosen = None

            if n_ops == 2:
                eligible = [
                    x for x in candidate_info if x["support_n"] == 2
                ]
                if eligible:
                    pair_distance = min(
                        dist[(i, j)]
                        for i in valid
                        for j in valid
                        if i < j
                    )

                    recommendation_rows.append({
                        "shared_stop_group_id": gid,
                        "physical_location_id": loc_id,
                        "physical_location_match": loc["physical_location_match"],
                        "group_confidence": group_conf.get(str(gid), ""),
                        "recommendation_status_code":
                            "AGREEMENT_WITHIN_25FT_NO_REFERENCE",
                        "recommended_source_key": "",
                        "recommended_agency": "",
                        "recommended_stop_id": "",
                        "recommended_lat": "",
                        "recommended_lon": "",
                        "recommendation_method":
                            "TWO_OPERATOR_AGREEMENT_WITHIN_25FT",
                        "recommendation_confidence": "",
                        "recommendation_support_operator_count": 2,
                        "physical_location_operator_count": 2,
                        "physical_location_record_count": len(g),
                        "two_operator_agreement_distance_ft": round(pair_distance, 2),
                        "source_keys": " | ".join(source_keys),
                    })

                    for idx in g.index:
                        df.at[idx, "recommendation_status_code"] = (
                            "AGREEMENT_WITHIN_25FT_NO_REFERENCE"
                        )
                        df.at[idx, "recommendation_method"] = (
                            "TWO_OPERATOR_AGREEMENT_WITHIN_25FT"
                        )
                        df.at[idx, "recommendation_support_operator_count"] = "2"
                        df.at[idx, "over_25ft"] = "N"
                        df.at[idx, "verification_needed"] = "N"

                    continue

                reason = "TWO_OPERATOR_DISAGREEMENT_OVER_25FT"

            else:
                eligible = [
                    x for x in candidate_info
                    if x["support_n"] >= required_majority
                    and x["support_n"] == max_support
                ]

                if not eligible:
                    reason = "NO_OPERATOR_MAJORITY_WITHIN_25FT"
                else:
                    coalitions = {}
                    for x in eligible:
                        key = tuple(sorted(x["support_ops"]))
                        coalitions.setdefault(key, []).append(x)

                    if len(coalitions) > 1:
                        reps = [
                            sorted(
                                items,
                                key=lambda x: (
                                    x["max_support_dist"],
                                    x["sum_support_dist"],
                                    _clean(df.at[x["candidate_index"], source_c]),
                                ),
                            )[0]
                            for items in coalitions.values()
                        ]

                        competing = False
                        for i, left in enumerate(reps):
                            for right in reps[i + 1:]:
                                if (
                                    dist[(left["candidate_index"], right["candidate_index"])]
                                    > issue_threshold_ft + 1e-9
                                ):
                                    competing = True
                                    break
                            if competing:
                                break

                        if competing:
                            reason = "COMPETING_OPERATOR_MAJORITY_CLUSTERS"
                        else:
                            eligible = reps

                    if not reason:
                        chosen = sorted(
                            eligible,
                            key=lambda x: (
                                -x["support_n"],
                                x["max_support_dist"],
                                x["sum_support_dist"],
                                _clean(df.at[x["candidate_index"], source_c]),
                            ),
                        )[0]
                        resolved = True
                        method = (
                            "EXISTING_POINT_OPERATOR_MAJORITY_WITHIN_25FT"
                        )
                        recommendation_conf = (
                            "HIGH" if chosen["support_n"] >= 3 else "MEDIUM"
                        )

            if not resolved:
                for idx in g.index:
                    df.at[idx, "recommendation_status_code"] = "UNRESOLVED"
                    df.at[idx, "verification_needed"] = "Y"
                    df.at[idx, "recommendation_review_reason"] = reason

                unresolved_rows.append({
                    "shared_stop_group_id": gid,
                    "physical_location_id": loc_id,
                    "physical_location_match": loc["physical_location_match"],
                    "group_confidence": group_conf.get(str(gid), ""),
                    "recommendation_review_reason": reason,
                    "operator_count": n_ops,
                    "record_count": len(g),
                    "max_operator_support_within_25ft": max_support,
                    "required_operator_majority": required_majority,
                    "source_keys": " | ".join(source_keys),
                })
                continue

            candidate_index = chosen["candidate_index"]
            supporters = chosen["supporters"]
            supporter_set = set(supporters)
            supporter_keys = [
                _clean(df.at[j, source_c]) for j in supporters
            ]

            recommended_source = _clean(df.at[candidate_index, source_c])
            recommended_agency_name = _clean(df.at[candidate_index, agency_c])
            recommended_stop = _clean(df.at[candidate_index, stop_id_c])
            recommended_lat = coords[candidate_index][0]
            recommended_lon = coords[candidate_index][1]

            recommendation_rows.append({
                "shared_stop_group_id": gid,
                "physical_location_id": loc_id,
                "physical_location_match": loc["physical_location_match"],
                "group_confidence": group_conf.get(str(gid), ""),
                "recommendation_status_code": "RESOLVED_EXISTING_POINT",
                "recommended_source_key": recommended_source,
                "recommended_agency": recommended_agency_name,
                "recommended_stop_id": recommended_stop,
                "recommended_lat": recommended_lat,
                "recommended_lon": recommended_lon,
                "recommendation_method": method,
                "recommendation_confidence": recommendation_conf,
                "recommendation_support_operator_count": chosen["support_n"],
                "physical_location_operator_count": n_ops,
                "physical_location_record_count": len(g),
                "source_keys": " | ".join(source_keys),
            })

            for idx in g.index:
                df.at[idx, "recommendation_status_code"] = (
                    "RESOLVED_EXISTING_POINT"
                )
                df.at[idx, "recommended_source_key"] = recommended_source
                df.at[idx, "recommended_agency"] = recommended_agency_name
                df.at[idx, "recommended_stop_id"] = recommended_stop
                df.at[idx, "recommended_lat"] = recommended_lat
                df.at[idx, "recommended_lon"] = recommended_lon
                df.at[idx, "recommendation_method"] = method
                df.at[idx, "recommendation_confidence"] = recommendation_conf
                df.at[idx, "recommendation_support_operator_count"] = str(
                    chosen["support_n"]
                )

                if idx == candidate_index:
                    df.at[idx, "recommended_point_flag"] = "Y"

                lat = _safe_float(df.at[idx, lat_c])
                lon = _safe_float(df.at[idx, lon_c])
                if lat is None or lon is None:
                    df.at[idx, "verification_needed"] = "Y"
                    df.at[idx, "recommendation_review_reason"] = (
                        "MISSING_SOURCE_COORDINATE"
                    )
                    continue

                dref = _haversine_ft(lat, lon, recommended_lat, recommended_lon)
                df.at[idx, "distance_to_recommended_ft"] = f"{dref:.2f}"

                over25 = dref > issue_threshold_ft + 1e-9
                df.at[idx, "over_25ft"] = "Y" if over25 else "N"

                min_support_dist = min(
                    _haversine_ft(
                        lat, lon,
                        coords[sidx][0], coords[sidx][1],
                    )
                    for sidx in supporter_set
                )

                spatial_outlier = (
                    over25
                    and min_support_dist > issue_threshold_ft + 1e-9
                )

                if not spatial_outlier:
                    df.at[idx, "verification_needed"] = "N"
                    continue

                candidate_source = _clean(df.at[idx, source_c])
                best_direct, _ = _best_direct_pair_evidence(
                    candidate_source, supporter_keys, pair_lookup
                )

                suppress_reason = ""
                if n_ops < 3:
                    suppress_reason = (
                        "TWO_OPERATOR_LOCATION_NO_AUTOMATIC_POSITION_ISSUE"
                    )
                elif not best_direct or not best_direct["qualifies"]:
                    suppress_reason = (
                        "NO_DIRECT_LIKELY_SHARED_STOP_EVIDENCE_TO_CONSENSUS"
                    )

                if suppress_reason:
                    df.at[idx, "verification_needed"] = "Y"
                    df.at[idx, "recommendation_review_reason"] = suppress_reason
                    suppressed_rows.append({
                        "shared_stop_group_id": gid,
                        "physical_location_id": loc_id,
                        "source_key": candidate_source,
                        "agency": _clean(df.at[idx, agency_c]),
                        "stop_id": _clean(df.at[idx, stop_id_c]),
                        "stop_name": _clean(df.at[idx, stop_name_c]),
                        "distance_to_recommended_ft": round(dref, 2),
                        "min_distance_to_consensus_ft": round(
                            min_support_dist, 2
                        ),
                        "recommendation_support_operator_count": chosen["support_n"],
                        "physical_location_operator_count": n_ops,
                        "suppression_reason": suppress_reason,
                    })
                    continue

                issue_conf = (
                    "HIGH" if chosen["support_n"] >= 3 else "MEDIUM"
                )

                df.at[idx, "likely_incorrect_stop_flag"] = "Y"
                df.at[idx, "verification_needed"] = "Y"
                df.at[idx, "recommendation_review_reason"] = (
                    "OVER_25FT_WITH_OPERATOR_CONSENSUS_AND_DIRECT_SAME_STOP_EVIDENCE"
                )
                df.at[idx, "issue_confidence"] = issue_conf
                df.at[idx, "issue_direct_pair_score"] = str(
                    best_direct["score"]
                )
                df.at[idx, "issue_direct_pair_classification"] = (
                    best_direct["classification"]
                )
                df.at[idx, "issue_direct_pair_evidence"] = (
                    best_direct["evidence"]
                )

                issue_rows.append({
                    "issue_type": "STOP_POSITION_OVER_25FT",
                    "issue_confidence": issue_conf,
                    "shared_stop_group_id": gid,
                    "physical_location_id": loc_id,
                    "physical_location_match": loc["physical_location_match"],
                    "likely_incorrect_source_key": candidate_source,
                    "likely_incorrect_agency": _clean(df.at[idx, agency_c]),
                    "likely_incorrect_stop_id": _clean(df.at[idx, stop_id_c]),
                    "likely_incorrect_stop_name": _clean(
                        df.at[idx, stop_name_c]
                    ),
                    "likely_incorrect_lat": lat,
                    "likely_incorrect_lon": lon,
                    "recommended_source_key": recommended_source,
                    "recommended_agency": recommended_agency_name,
                    "recommended_stop_id": recommended_stop,
                    "recommended_lat": recommended_lat,
                    "recommended_lon": recommended_lon,
                    "distance_to_recommended_ft": round(dref, 2),
                    "min_distance_to_consensus_ft": round(
                        min_support_dist, 2
                    ),
                    "recommendation_confidence": recommendation_conf,
                    "recommendation_method": method,
                    "recommendation_support_operator_count": chosen["support_n"],
                    "group_operator_count": n_ops,
                    "physical_location_operator_count": n_ops,
                    "group_confidence": group_conf.get(str(gid), ""),
                    "direct_pair_score": best_direct["score"],
                    "direct_pair_classification": (
                        best_direct["classification"]
                    ),
                    "direct_pair_distance_ft": best_direct["distance_ft"],
                    "direct_pair_strong_identity_evidence": (
                        best_direct["strong_identity_evidence"]
                    ),
                    "direct_pair_evidence": best_direct["evidence"],
                    "verification_needed": "Y",
                    "evidence": (
                        f"{chosen['support_n']} of {n_ops} agencies support "
                        "an existing recommended point within 25 ft; the candidate "
                        f"is {dref:.1f} ft from that recommended point and has direct "
                        "likely same-stop evidence to the consensus."
                    ),
                })

    locations = pd.DataFrame(location_rows)
    recommendations = pd.DataFrame(recommendation_rows)
    issues = pd.DataFrame(issue_rows)
    unresolved = pd.DataFrame(unresolved_rows)
    suppressed = pd.DataFrame(suppressed_rows)

    return df, recommendations, issues, unresolved, suppressed
