# MobilityData Catalog API: Database Engine Recommendation

This document's purpose is to share our recent findings regarding the selection of an appropriate database engine for the initial phase of the MobilityData catalog API. After a careful analysis of several potential candidates, we have concluded that **PostgreSQL** would be the most effective solution.

## Evaluation Criteria

The main use cases extracted from the production requirement document are as follows:

1. **Data Discovery and Consumption:** Users need to easily discover and access the available data for GTFS and GBFS.

2. **Data Filtering:** Efficient data retrieval is needed to filter data by various criteria like bounding boxes, report URL, operator, feature, and status.

3. **Large Dataset Management:** The system must efficiently handle large datasets.

4. **Geospatial Data Support:** The ability to manage geospatial data.

In addition, we have considered the following important factors:

- **Open Source Context:** Given that we operate in an open-source context, we need robust community support and thorough documentation. We also have prioritized open-source engines.

- **Learning Curve:** The chosen database engine should have a manageable learning curve for our contributors and our internal team.

- **Cost-Effectiveness:** The database engine should be affordable.

- **Scalability:** We require a scalable solution to grow with our needs.

## Selection Process

Initially, we considered ten database engines: Oracle, MySQL, Microsoft SQL Server, PostgreSQL, MongoDB, Redis, IBM DB2, Elasticsearch, Microsoft Access, and SQLite.

After eliminating some based on factors such as large dataset handling capabilities, geospatial data support, cost-effectiveness, and open-source availability, we ended up with five final candidates: MySQL, PostgreSQL, Elasticsearch, MongoDB, and Redis.

## Final Candidates

### MySQL

MySQL supports large datasets and has built-in security features. It is lightweight, easy to use, reliable, and offers some geospatial data capabilities.

### PostgreSQL

PostgreSQL offers support for structured and unstructured data through JSON and user-defined types. It handles large datasets well, has encrypted access control for security, and shows excellent performance for complex queries. Its advanced geospatial data capabilities are a major advantage.

### Elasticsearch

Elasticsearch is a distributed, document-oriented database with search capabilities for structured and unstructured data. Its performance is excellent for full-text search.

### MongoDB

MongoDB is a document-oriented database supporting large document sizes and JSON-based queries. It offers data type flexibility and easy setup.

### Redis

Redis is an in-memory data structure store that allows high-speed data access and manipulation. It supports geospatial queries, but since data is loaded in memory, it is not suitable for large datasets.

## Why PostgreSQL?

While MongoDB was a close contender, we chose PostgreSQL for several reasons:

1. **More Comprehensive Geospatial Support:** PostgreSQL's geospatial support is more comprehensive than MongoDB's.

2. **Stronger Community Support and Documentation:** PostgreSQL, as an open-source solution, has extensive community support and well-maintained documentation, which are critical for our open source context.

3. **Support for Structured and Unstructured Data:** PostgreSQL's ability to handle both types of data offers us more flexibility.

4. **Scalability:** PostgreSQL's scalability features, including both vertical and horizontal scalability, make it a future-proof choice for managing our datasets.

We believe that PostgreSQL is the best choice for the first phase of the MobilityData catalog API given these strong points.
