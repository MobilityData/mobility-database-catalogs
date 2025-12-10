## Feed Submission Checklist

- [ ] **_Valid Direct Download URL:_** Does the URL produce a zip file and is it valid gtfs? If realtime, is it a protobuf?
- [ ] **_Official Status:_** Is the feed official? Check contact email, direct download URL, website etc.
- [ ] **_Authentication:_** Is there any authentication required?

### Is Your Feed New?

- [ ] **_MDB Stable ID:_** Correct stable id in the file name? And the “latest url” field? (if schedule feed)
- [ ] **_Sequential Ordering:_** Does the stable id increment from latest stable id? Do they increase in sequential order?

### Is Your Feed an Update?

- [ ] **_Official Status:_** If unofficial, do not deprecate and redirect the old feed, but import this new feed as unofficial so both feeds are available in the database
- [ ] **_Deprecate and Redirect:_** If official, deprecate and redirect the old feed to this updated feed

### Is it a Schedule Feed?

- [ ] **_Service Status:_** Is the status active? Check feed_info file for service window

### Is it a Realtime Feed?

- [ ] **_Reference:_** Does it have a reference to the schedule feed?

### Pre-existing Feed Existence [internal]

- [ ] Perform a check on the mobility database website to check for pre-existing unpublished (wip) feeds from other sources
- [ ] Sometimes the "old" feed is not included in the feed submission form, perform a check for fuzzy matches on Provider and Direct Download URL. In the case of probably matches, check with the validator for entity count, agency and feed info matches as well.

### Other Considerations [internal]

- [ ] **_Flex:_** Flex feeds are sometimes produced separately from schedule feeds. Import the flex feed as a brand new feed instead of a redirect of the schedule feed.
- [ ] **_Schedule Feed_**: Sometimes you will encounter two **active** schedule feeds. This may occur when one schedule feed is used as the schedule, while the other is used for a reference to the realtime feed. Look for feeds produced by Passio (or other vehicle tracking software).
