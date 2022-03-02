from abc import ABC, abstractmethod
import os
import json
from tools.helpers import (
    are_overlapping_boxes,
    is_readable,
    load_gtfs,
    extract_gtfs_bounding_box,
    get_iso_time,
    create_latest_url,
    to_json,
    create_filename,
)
from tools.constants import (
    GTFS_SCHEDULE_CATALOG_PATH,
    SOURCE_CATALOG_PATH_FROM_ROOT,
    GTFS_REALTIME_CATALOG_PATH,
    MDB_SOURCE_ID,
    DATA_TYPE,
    PROVIDER,
    NAME,
    LOCATION,
    COUNTRY_CODE,
    SUBDIVISION_NAME,
    MUNICIPALITY,
    BOUNDING_BOX,
    MINIMUM_LATITUDE,
    MAXIMUM_LATITUDE,
    MINIMUM_LONGITUDE,
    MAXIMUM_LONGITUDE,
    EXTRACTED_ON,
    URLS,
    AUTO_DISCOVERY,
    LICENSE,
    LATEST,
    STATIC_REFERENCE,
    REALTIME_VEHICLE_POSITIONS,
    REALTIME_TRIP_UPDATES,
    REALTIME_ALERTS,
    GTFS,
    GTFS_RT,
    JSON,
    ROOT,
    PATH,
    ENTITY_CLS,
    ID_KEY,
    UNKNOWN,
    FILENAME,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


class Catalog(ABC):
    root = None
    path = None
    catalog = None

    def __init__(self, **kwargs):
        if self.root is None:
            self.root = kwargs.pop(ROOT)
        if self.path is None:
            self.path = kwargs.pop(PATH)
        if self.catalog is None:
            self.catalog = self.aggregate(
                catalog_path=os.path.join(self.root, self.path),
                id_key=kwargs.pop(ID_KEY),
                entity_cls=kwargs.pop(ENTITY_CLS),
            )

    @staticmethod
    def identify(catalog_root):
        return sum(len(files) for path, sub_dirs, files in os.walk(catalog_root)) + 1

    @staticmethod
    def aggregate(catalog_path, id_key, entity_cls):
        catalog = {}
        for path, sub_dirs, files in os.walk(catalog_path):
            for file in files:
                with open(os.path.join(path, file)) as fp:
                    entity_json = json.load(fp)
                    entity_id = entity_json[id_key]
                    catalog[entity_id] = entity_cls(filename=file, **entity_json)
        return catalog

    @abstractmethod
    def add(self, **kwargs):
        pass

    @abstractmethod
    def update(self, **kwargs):
        pass


class SourcesCatalog(Catalog):
    def __init__(self, **kwargs):
        self.entity_cls = kwargs.pop(ENTITY_CLS)
        super().__init__(id_key=MDB_SOURCE_ID, entity_cls=self.entity_cls, **kwargs)

    def get_source(self, source_id):
        return self.catalog.get(source_id)

    def get_sources(self):
        return {
            source_id: source.as_json() for source_id, source in self.catalog.items()
        }

    def get_sources_by_bounding_box(
        self, minimum_latitude, maximum_latitude, minimum_longitude, maximum_longitude
    ):
        return {
            source_id: source.as_json()
            for source_id, source in self.catalog.items()
            if source.is_overlapping_bounding_box(
                minimum_latitude, maximum_latitude, minimum_longitude, maximum_longitude
            )
        }

    def get_sources_by_subdivision_name(self, subdivision_name):
        return {
            source_id: source.as_json()
            for source_id, source in self.catalog.items()
            if source.has_subdivision_name(subdivision_name)
        }

    def get_sources_by_country_code(self, country_code):
        return {
            source_id: source.as_json()
            for source_id, source in self.catalog.items()
            if source.has_country_code(country_code)
        }

    def get_latest_datasets(self):
        return {
            source_id: source.latest_url
            for source_id, source in self.catalog.items()
            if source.has_latest_dataset()
        }

    def add(self, **kwargs):
        mdb_source_id = self.identify(self.root)
        entity = self.entity_cls.build(mdb_source_id=mdb_source_id, **kwargs)
        if isinstance(entity, self.entity_cls):
            self.catalog[mdb_source_id] = entity
            self.save(entity)
        return self.catalog

    def update(self, **kwargs):
        mdb_source_id = kwargs.pop(MDB_SOURCE_ID)
        source = self.get_source(source_id=mdb_source_id)
        if source is not None:
            entity = source.update(mdb_source_id=mdb_source_id, **kwargs)
            self.catalog[mdb_source_id] = entity
            self.save(entity)
        return self.catalog

    def save(self, entity):
        return to_json(
            path=os.path.join(
                self.root,
                self.path,
                entity.filename,
            ),
            obj=entity.as_json(),
        )


class GtfsScheduleSourcesCatalog(SourcesCatalog):
    _instance = None

    def __init__(self, **kwargs):
        super().__init__(
            entity_cls=GtfsScheduleSource,
            root=os.path.join(PROJECT_ROOT, SOURCE_CATALOG_PATH_FROM_ROOT),
            path=GTFS_SCHEDULE_CATALOG_PATH,
            **kwargs,
        )

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls)
        return cls._instance


class GtfsRealtimeSourcesCatalog(SourcesCatalog):
    _instance = None

    def __init__(self, **kwargs):
        super().__init__(
            entity_cls=GtfsRealtimeSource,
            root=os.path.join(PROJECT_ROOT, SOURCE_CATALOG_PATH_FROM_ROOT),
            path=GTFS_REALTIME_CATALOG_PATH,
            **kwargs,
        )

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls)
        return cls._instance


class Source(ABC):
    def __init__(self, **kwargs):
        self.mdb_source_id = kwargs.pop(MDB_SOURCE_ID)
        self.data_type = kwargs.pop(DATA_TYPE)
        self.provider = kwargs.pop(PROVIDER)
        self.name = kwargs.pop(NAME, None)
        self.filename = kwargs.pop(FILENAME)

    @abstractmethod
    def __str__(self):
        pass

    @abstractmethod
    def __repr__(self):
        pass

    @abstractmethod
    def has_subdivision_name(self, subdivision_name):
        pass

    @abstractmethod
    def has_country_code(self, country_code):
        pass

    @abstractmethod
    def is_overlapping_bounding_box(
        self, minimum_latitude, maximum_latitude, minimum_longitude, maximum_longitude
    ):
        pass

    @abstractmethod
    def has_latest_dataset(self):
        pass

    @abstractmethod
    def update(self, **kwargs):
        pass

    @classmethod
    @abstractmethod
    def build(cls, **kwargs):
        pass

    @classmethod
    @abstractmethod
    def schematize(cls, **kwargs):
        pass

    def as_json(self):
        return json.loads(self.__str__())


class GtfsScheduleSource(Source):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        location = kwargs.pop(LOCATION, {})
        self.country_code = location.pop(COUNTRY_CODE)
        self.subdivision_name = location.pop(SUBDIVISION_NAME)
        self.municipality = location.pop(MUNICIPALITY)
        bounding_box = location.pop(BOUNDING_BOX, {})
        self.bbox_min_lat = bounding_box.pop(MINIMUM_LATITUDE)
        self.bbox_max_lat = bounding_box.pop(MAXIMUM_LATITUDE)
        self.bbox_min_lon = bounding_box.pop(MINIMUM_LONGITUDE)
        self.bbox_max_lon = bounding_box.pop(MAXIMUM_LONGITUDE)
        self.bbox_extracted_on = bounding_box.pop(EXTRACTED_ON)
        urls = kwargs.pop(URLS, {})
        self.auto_discovery_url = urls.pop(AUTO_DISCOVERY)
        self.latest_url = urls.pop(LATEST)
        self.license_url = urls.pop(LICENSE, None)

    def __str__(self):
        attributes = {
            MDB_SOURCE_ID: self.mdb_source_id,
            DATA_TYPE: self.data_type,
            PROVIDER: self.provider,
            NAME: self.name,
            COUNTRY_CODE: self.country_code,
            SUBDIVISION_NAME: self.subdivision_name,
            MUNICIPALITY: self.municipality,
            MINIMUM_LATITUDE: self.bbox_min_lat,
            MAXIMUM_LATITUDE: self.bbox_max_lat,
            MINIMUM_LONGITUDE: self.bbox_min_lon,
            MAXIMUM_LONGITUDE: self.bbox_max_lon,
            EXTRACTED_ON: self.bbox_extracted_on,
            AUTO_DISCOVERY: self.auto_discovery_url,
            LATEST: self.latest_url,
            LICENSE: self.license_url,
        }
        return json.dumps(self.schematize(**attributes))

    def __repr__(self):
        return f"GtfsScheduleSource({self.__str__()})"

    def has_subdivision_name(self, subdivision_name):
        return self.subdivision_name == subdivision_name

    def has_country_code(self, country_code):
        return self.country_code == country_code

    def is_overlapping_bounding_box(
        self, minimum_latitude, maximum_latitude, minimum_longitude, maximum_longitude
    ):
        return are_overlapping_boxes(
            source_minimum_latitude=self.bbox_min_lat,
            source_maximum_latitude=self.bbox_max_lat,
            source_minimum_longitude=self.bbox_min_lon,
            source_maximum_longitude=self.bbox_max_lon,
            filter_minimum_latitude=minimum_latitude,
            filter_maximum_latitude=maximum_latitude,
            filter_minimum_longitude=minimum_longitude,
            filter_maximum_longitude=maximum_longitude,
        )

    def has_latest_dataset(self):
        return self.latest_url is not None

    def update(self, **kwargs):
        auto_discovery_url = kwargs.get(AUTO_DISCOVERY)
        if auto_discovery_url is not None and is_readable(
            url=auto_discovery_url, load_func=load_gtfs()
        ):
            self.auto_discovery_url = auto_discovery_url
            (
                self.bbox_min_lat,
                self.bbox_max_lat,
                self.bbox_min_lon,
                self.bbox_max_lon,
            ) = extract_gtfs_bounding_box(url=auto_discovery_url)
            self.bbox_extracted_on = get_iso_time()
        provider = kwargs.get(PROVIDER)
        if provider is not None:
            self.provider = provider
        name = kwargs.get(NAME)
        if name is not None:
            self.name = name
        country_code = kwargs.get(COUNTRY_CODE)
        if country_code is not None:
            self.country_code = country_code
        subdivision_name = kwargs.get(SUBDIVISION_NAME)
        if subdivision_name is not None:
            self.subdivision_name = subdivision_name
        municipality = kwargs.get(MUNICIPALITY)
        if municipality is not None:
            self.municipality = municipality
        license_url = kwargs.get(LICENSE)
        if license_url is not None:
            self.license_url = license_url
        return self

    @classmethod
    def build(cls, **kwargs):
        instance = None
        auto_discovery_url = kwargs.get(AUTO_DISCOVERY)
        if is_readable(url=auto_discovery_url, load_func=load_gtfs):
            data_type = GTFS
            (
                minimum_latitude,
                maximum_latitude,
                minimum_longitude,
                maximum_longitude,
            ) = extract_gtfs_bounding_box(url=auto_discovery_url)
            extracted_on = get_iso_time()
            filename = create_filename(
                country_code=kwargs.get(COUNTRY_CODE),
                subdivision_name=kwargs.get(SUBDIVISION_NAME),
                provider=kwargs.get(PROVIDER),
                data_type=data_type,
                mdb_source_id=kwargs.get(MDB_SOURCE_ID),
                extension=JSON,
            )
            latest = create_latest_url(
                country_code=kwargs.get(COUNTRY_CODE),
                subdivision_name=kwargs.get(SUBDIVISION_NAME),
                provider=kwargs.get(PROVIDER),
                data_type=data_type,
                mdb_source_id=kwargs.get(MDB_SOURCE_ID),
            )
            schema = cls.schematize(
                data_type=data_type,
                minimum_latitude=minimum_latitude,
                maximum_latitude=maximum_latitude,
                minimum_longitude=minimum_longitude,
                maximum_longitude=maximum_longitude,
                extracted_on=extracted_on,
                latest=latest,
                **kwargs,
            )
            instance = cls(filename=filename, **schema)
        return instance

    @classmethod
    def schematize(cls, **kwargs):
        schema = {
            MDB_SOURCE_ID: kwargs.pop(MDB_SOURCE_ID),
            DATA_TYPE: kwargs.pop(DATA_TYPE),
            PROVIDER: kwargs.pop(PROVIDER),
            NAME: kwargs.pop(NAME, None),
            LOCATION: {
                COUNTRY_CODE: kwargs.pop(COUNTRY_CODE),
                SUBDIVISION_NAME: kwargs.pop(SUBDIVISION_NAME),
                MUNICIPALITY: kwargs.pop(MUNICIPALITY),
                BOUNDING_BOX: {
                    MINIMUM_LATITUDE: kwargs.pop(MINIMUM_LATITUDE),
                    MAXIMUM_LATITUDE: kwargs.pop(MAXIMUM_LATITUDE),
                    MINIMUM_LONGITUDE: kwargs.pop(MINIMUM_LONGITUDE),
                    MAXIMUM_LONGITUDE: kwargs.pop(MAXIMUM_LONGITUDE),
                    EXTRACTED_ON: kwargs.pop(EXTRACTED_ON),
                },
            },
            URLS: {
                AUTO_DISCOVERY: kwargs.pop(AUTO_DISCOVERY),
                LATEST: kwargs.pop(LATEST),
                LICENSE: kwargs.pop(LICENSE, None),
            },
        }
        if schema[NAME] is None:
            del schema[NAME]
        if schema[URLS][LICENSE] is None:
            del schema[URLS][LICENSE]
        return schema


class GtfsRealtimeSource(Source):
    static_catalog = GtfsScheduleSourcesCatalog()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.static_reference = kwargs.pop(STATIC_REFERENCE, None)
        urls = kwargs.pop(URLS, {})
        self.vehicle_positions_url = urls.pop(REALTIME_VEHICLE_POSITIONS, None)
        self.trip_updates_url = urls.pop(REALTIME_TRIP_UPDATES, None)
        self.service_alerts_url = urls.pop(REALTIME_ALERTS, None)

    def __str__(self):
        attributes = {
            MDB_SOURCE_ID: self.mdb_source_id,
            DATA_TYPE: self.data_type,
            PROVIDER: self.provider,
            NAME: self.name,
            STATIC_REFERENCE: self.static_reference,
            REALTIME_VEHICLE_POSITIONS: self.vehicle_positions_url,
            REALTIME_TRIP_UPDATES: self.trip_updates_url,
            REALTIME_ALERTS: self.service_alerts_url,
        }
        return json.dumps(self.schematize(**attributes))

    def __repr__(self):
        return f"GtfsRealtimeSource({self.__str__()})"

    @classmethod
    def get_static_source(cls, static_reference):
        return cls.static_catalog.get_source(static_reference)

    def has_subdivision_name(self, subdivision_name):
        static_source = self.get_static_source(self.static_reference)
        return (
            static_source.subdivision_name == subdivision_name
            if static_source is not None
            else False
        )

    def has_country_code(self, country_code):
        static_source = self.get_static_source(self.static_reference)
        return (
            static_source.country_code == country_code
            if static_source is not None
            else False
        )

    def is_overlapping_bounding_box(
        self, minimum_latitude, maximum_latitude, minimum_longitude, maximum_longitude
    ):
        static_source = self.get_static_source(self.static_reference)
        return (
            are_overlapping_boxes(
                source_minimum_latitude=static_source.bbox_min_lat,
                source_maximum_latitude=static_source.bbox_max_lat,
                source_minimum_longitude=static_source.bbox_min_lon,
                source_maximum_longitude=static_source.bbox_max_lon,
                filter_minimum_latitude=minimum_latitude,
                filter_maximum_latitude=maximum_latitude,
                filter_minimum_longitude=minimum_longitude,
                filter_maximum_longitude=maximum_longitude,
            )
            if static_source is not None
            else False
        )

    def has_latest_dataset(self):
        return False

    def update(self, **kwargs):
        provider = kwargs.get(PROVIDER)
        if provider is not None:
            self.provider = provider
        name = kwargs.get(NAME)
        if name is not None:
            self.name = name
        static_reference = kwargs.get(STATIC_REFERENCE)
        if static_reference is not None:
            self.static_reference = static_reference
        vehicle_positions_url = kwargs.get(REALTIME_VEHICLE_POSITIONS)
        if vehicle_positions_url is not None:
            self.vehicle_positions_url = vehicle_positions_url
        trip_updates_url = kwargs.get(REALTIME_TRIP_UPDATES)
        if trip_updates_url is not None:
            self.trip_updates_url = trip_updates_url
        service_alerts_url = kwargs.get(REALTIME_ALERTS)
        if service_alerts_url is not None:
            self.service_alerts_url = service_alerts_url
        return self

    @classmethod
    def build(cls, **kwargs):
        data_type = GTFS_RT
        static_reference = kwargs.get(STATIC_REFERENCE)
        static_source = (
            cls.get_static_source(static_reference)
            if static_reference is not None
            else None
        )
        country_code = (
            static_source.country_code if static_source is not None else UNKNOWN
        )
        subdivision_name = (
            static_source.subdivision_name if static_source is not None else UNKNOWN
        )
        filename = create_filename(
            country_code=country_code,
            subdivision_name=subdivision_name,
            provider=kwargs.get(PROVIDER),
            data_type=data_type,
            mdb_source_id=kwargs.get(MDB_SOURCE_ID),
            extension=JSON,
        )
        schema = cls.schematize(data_type=data_type, **kwargs)
        instance = cls(filename=filename, **schema)
        return instance

    @classmethod
    def schematize(cls, **kwargs):
        schema = {
            MDB_SOURCE_ID: kwargs.pop(MDB_SOURCE_ID),
            DATA_TYPE: kwargs.pop(DATA_TYPE),
            PROVIDER: kwargs.pop(PROVIDER),
            NAME: kwargs.pop(NAME, None),
            STATIC_REFERENCE: kwargs.pop(STATIC_REFERENCE, None),
            URLS: {
                REALTIME_VEHICLE_POSITIONS: kwargs.pop(
                    REALTIME_VEHICLE_POSITIONS, None
                ),
                REALTIME_TRIP_UPDATES: kwargs.pop(REALTIME_TRIP_UPDATES, None),
                REALTIME_ALERTS: kwargs.pop(REALTIME_ALERTS, None),
            },
        }
        if schema[NAME] is None:
            del schema[NAME]
        if schema[STATIC_REFERENCE] is None:
            del schema[STATIC_REFERENCE]
        if schema[URLS][REALTIME_VEHICLE_POSITIONS] is None:
            del schema[URLS][REALTIME_VEHICLE_POSITIONS]
        if schema[URLS][REALTIME_TRIP_UPDATES] is None:
            del schema[URLS][REALTIME_TRIP_UPDATES]
        if schema[URLS][REALTIME_ALERTS] is None:
            del schema[URLS][REALTIME_ALERTS]
        return schema
