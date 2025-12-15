## Feed Submission Checklist

Thanks for contributing to the MobilityDatabase!

This is a comprehensive checklist detailing the things to consider before submitting a feed to the database. The schema links in this checklist will follow the convention of [[1]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/schemas/gtfs_schedule_source_schema.json) for schedule feed schema and [[2]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/schemas/gtfs_realtime_source_schema.json) for realtime feeds. You will find the schema definitions for schedule and realtime feeds are often the same, but both references are always included for completeness. If you have any questions, reach out to @ianktc.

### General Checks

- [ ] **_Valid Direct Download URL:_** Does the URL produce a zip file and is it valid gtfs? [[1]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/schemas/gtfs_schedule_source_schema.json#L117-L121) If realtime, is it a protobuf? [[2]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/schemas/gtfs_realtime_source_schema.json#L62-L66)
- [ ] **_Official Status:_** Is the feed official? Check contact email, direct download URL, website etc. [[1]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/schemas/gtfs_schedule_source_schema.json#L205-L209) or [[2]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/schemas/gtfs_realtime_source_schema.json#L175-L179)
- [ ] **_Service Status:_** Is the status active? Check feed_info file for service window. [[1]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/schemas/gtfs_schedule_source_schema.json#L109-L113) or [[2]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/schemas/gtfs_realtime_source_schema.json#L50-L54)
- [ ] **_Authentication:_** Is there any authentication required? [[1]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/schemas/gtfs_schedule_source_schema.json#L122-L139) or [[2]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/schemas/gtfs_realtime_source_schema.json#L67-L85) Enum values are described [[1]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/README.md?plain=1#L76) and [[2]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/README.md?plain=1#L102) (they are the same)

### Is Your Feed New?

- [ ] **_MDB Stable ID:_** Correct stable id in the file name? Does it match the mdb_source_id field? [[1]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/schemas/gtfs_schedule_source_schema.json#L6-L9) or [[2]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/schemas/gtfs_realtime_source_schema.json#L6-L9). And stable id in the “latest url” field? [[1]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/schemas/gtfs_schedule_source_schema.json#L140-L144)
- [ ] **_Sequential Ordering:_** Does the stable id increment from latest stable id? Do they increase in sequential order? Refer to this [spreadsheet](https://files.mobilitydatabase.org/feeds_v2.csv) for the latest mdb stable id.

### Is Your Feed an Update?

- [ ] **_Official Status:_** If unofficial, do not deprecate and redirect the old feed, but import this new feed as unofficial so both feeds are available in the database
- [ ] **_Deprecate and Redirect:_** If official, deprecate and redirect the old feed to this updated feed. [[1]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/schemas/gtfs_schedule_source_schema.json#L188-L204) or [[2]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/schemas/gtfs_realtime_source_schema.json#L158-L174)

### Is it a Realtime Feed?

- [ ] **_Reference:_** Does it have a reference to the schedule feed? [[2]](https://github.com/MobilityData/mobility-database-catalogs/blob/f01d27ed5f350fbff0d77038d362a3543915b289/schemas/gtfs_realtime_source_schema.json#L35-L41)

### Pre-existing Feed Existence [internal]

- [ ] Perform a check on the mobility database website to check for pre-existing unpublished (wip) feeds from other sources
- [ ] Sometimes the "old" feed is not included in the feed submission form, perform a check for fuzzy matches on Provider and Direct Download URL. In the case of probable matches, check with the validator for entity count, agency and feed info matches as well.

### Other Considerations [internal]

Sometimes you will encounter two **active** schedule feeds. There are some possible reasons this may occur:

- [ ] **_Flex:_** Flex feeds are sometimes produced separately from schedule feeds. Import the flex feed as a brand new feed instead of a redirect of the schedule feed. [[definition]](https://gtfs.org/community/extensions/flex/)
- [ ] **_Reference Schedule Feed_**:  One schedule feed may be used as the schedule, while the other is used as a reference to the realtime feed. Look for feeds produced by Passio (or other vehicle tracking software). [[example]](https://mobilitydatabase.org/feeds?q=toronto+transit+commission&gtfs=true)