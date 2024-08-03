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
    download_dataset,
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
    DIRECT_DOWNLOAD,
    LICENSE,
    LATEST,
    STATIC_REFERENCE,
    AUTHENTICATION_TYPE,
    AUTHENTICATION_INFO,
    API_KEY_PARAMETER_NAME,
    API_KEY_PARAMETER_VALUE,
    ENTITY_TYPE,
    NOTE,
    GTFS,
    GTFS_RT,
    JSON,
    ROOT,
    PATH,
    ENTITY_CLS,
    ID_KEY,
    UNKNOWN,
    FILENAME,
    FEATURES,
    STATUS,
    ACTIVE,
    FEED_CONTACT_EMAIL,
    REDIRECT_ID,
    REDIRECT_COMMENT,
    REDIRECTS,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


class Catalog(ABC):

    """
    An abstract base class representing a catalog of entities.

    This class provides a framework for managing a catalog of entities stored in a file system.
    It includes methods for initializing the catalog, identifying the number of entities,
    and aggregating entities from files.

    Attributes:
        root (str): The root directory of the catalog.
        path (str): The relative path to the catalog directory from the root.
        catalog (dict): A dictionary containing the aggregated entities.
    """

    root = None
    path = None
    catalog = None

    def __init__(self, **kwargs):
        """
        Initialize the Catalog instance.

        Args:
            **kwargs: Keyword arguments containing initialization parameters.
                Must include 'ROOT', 'PATH', 'ID_KEY', and 'ENTITY_CLS'.
        """
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
        """
        Identify the number of entities in the catalog.

        This method counts the total number of files in the catalog directory
        and its subdirectories, then adds 1 to the count.

        Args:
            catalog_root (str): The root directory of the catalog.

        Returns:
            int: The total number of files plus one.
        """
        return sum(len(files) for path, sub_dirs, files in os.walk(catalog_root)) + 1

    @staticmethod
    def aggregate(catalog_path, id_key, entity_cls):
        """
        Aggregate entities from files in the catalog directory.

        This method walks through the catalog directory, reads JSON files,
        and creates entity instances based on the file contents.

        Args:
            catalog_path (str): The path to the catalog directory.
            id_key (str): The key in the JSON data that represents the entity's ID.
            entity_cls (type): The class to use for creating entity instances.

        Returns:
            dict: A dictionary of entity instances, keyed by their IDs.
        """
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
        """
        Add a new entity to the catalog.

        This method must be implemented by subclasses.

        Args:
            **kwargs: Keyword arguments containing the entity data.

        Raises:
            NotImplementedError: If not implemented by a subclass.
        """
        pass

    @abstractmethod
    def update(self, **kwargs):
        """
        Update an existing entity in the catalog.

        This method must be implemented by subclasses.

        Args:
            **kwargs: Keyword arguments containing the updated entity data.

        Raises:
            NotImplementedError: If not implemented by a subclass.
        """
        pass


class SourcesCatalog(Catalog):

    """
    A class representing a catalog of data sources.

    This class extends the Catalog base class and provides specific functionality
    for managing collections of data sources. It is designed to work with various
    types of Source objects, as specified by the entity_cls parameter.

    Attributes:
        entity_cls (type): The class of the entities (sources) stored in this catalog.
            This is typically a subclass of the Source class.

    Note:
        This class inherits attributes and methods from the Catalog base class,
        including methods for aggregating, identifying, and managing catalog entries.
    """

    def __init__(self, **kwargs):
        """
        Initialize a SourcesCatalog instance.

        This method extends the parent class initializer, setting up the catalog
        with a specific entity class for the sources it will contain.

        Args:
            **kwargs: Keyword arguments containing the catalog's attributes.
                Must include ENTITY_CLS, specifying the class of sources to be stored.
                Other arguments are passed to the parent Catalog class.

        Raises:
            KeyError: If the required ENTITY_CLS key is not provided in kwargs.

        Note:
            The MDB_SOURCE_ID is used as the id_key for the catalog entries.
        """
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

    def get_sources_by_feature(self, feature):
        return {
            source_id: source.as_json()
            for source_id, source in self.catalog.items()
            if source.has_feature(feature)
        }

    def get_sources_by_status(self, status):
        return {
            source_id: source.as_json()
            for source_id, source in self.catalog.items()
            if source.has_status(status)
        }

    def add(self, **kwargs):
        mdb_source_id = self.identify(self.root)
        redirects = kwargs.pop(REDIRECTS, [])
        if redirects is not None and len(redirects) > 0:
            kwargs[REDIRECTS] = [
                {
                    REDIRECT_ID: elem.get(REDIRECT_ID), REDIRECT_COMMENT: elem.get(REDIRECT_COMMENT)
                }
                for elem in redirects
            ]
            kwargs[REDIRECTS] = list(filter(lambda x: x.get(REDIRECT_ID) != 'None', kwargs[REDIRECTS]))

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

    """
    A singleton class representing a catalog of GTFS (General Transit Feed Specification) schedule sources.

    This class extends the SourcesCatalog class and is specifically designed to manage
    GTFS schedule sources. It implements the Singleton pattern to ensure only one instance
    of the catalog exists throughout the application.

    Attributes:
        _instance (GtfsScheduleSourcesCatalog): The single instance of this class.
    """

    _instance = None

    def __init__(self, **kwargs):
        """
        Initialize the GtfsScheduleSourcesCatalog instance.

        This method calls the parent class constructor with specific parameters
        for GTFS schedule sources.

        Args:
            **kwargs: Additional keyword arguments to be passed to the parent constructor.
        """
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
    
    """
    A singleton class representing a catalog of GTFS (General Transit Feed Specification) realtime sources.

    This class extends the SourcesCatalog class and is specifically designed to manage
    GTFS realtime sources. It implements the Singleton pattern to ensure only one instance
    of the catalog exists throughout the application.

    Attributes:
        _instance (GtfsRealtimeSourcesCatalog): The single instance of this class.
    """

    _instance = None

    def __init__(self, **kwargs):
        """
        Initialize the GtfsRealtimeSourcesCatalog instance.

        This method calls the parent class constructor with specific parameters
        for GTFS realtime sources.

        Args:
            **kwargs: Additional keyword arguments to be passed to the parent constructor.
        """
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
    
    """
    An abstract base class representing a data source.

    This class provides a framework for managing various types of data sources,
    including their metadata, authentication information, and associated URLs.
    It defines a set of abstract methods that must be implemented by subclasses
    to provide specific functionality for different types of sources.

    Attributes:
        mdb_source_id (str): Unique identifier for the source in the database.
        data_type (str): The type of data this source provides.
        provider (str): The provider of the data source.
        name (str, optional): The name of the data source.
        filename (str): The filename associated with the data source.
        features (list, optional): A list of features associated with the data source.
        status (str, optional): The current status of the data source.
        direct_download_url (str): URL for direct download of the data.
        authentication_type (str, optional): The type of authentication required, if any.
        authentication_info_url (str, optional): URL for authentication information.
        api_key_parameter_name (str, optional): The name of the API key parameter, if applicable.
        license_url (str, optional): URL for the license information of the data.

    Note:
        This class is designed to be subclassed. Subclasses must implement
        all abstract methods defined here.
    """
    
    def __init__(self, **kwargs):
        self.mdb_source_id = kwargs.pop(MDB_SOURCE_ID)
        self.data_type = kwargs.pop(DATA_TYPE)
        self.provider = kwargs.pop(PROVIDER)
        self.name = kwargs.pop(NAME, None)
        self.filename = kwargs.pop(FILENAME)
        self.features = kwargs.pop(FEATURES, None)
        self.status = kwargs.pop(STATUS, None)
        urls = kwargs.get(URLS, {})
        self.direct_download_url = urls.pop(DIRECT_DOWNLOAD)
        self.authentication_type = urls.pop(AUTHENTICATION_TYPE, None)
        self.authentication_info_url = urls.pop(AUTHENTICATION_INFO, None)
        self.api_key_parameter_name = urls.pop(API_KEY_PARAMETER_NAME, None)
        self.license_url = urls.pop(LICENSE, None)

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
    def has_feature(self, feature):
        pass

    @abstractmethod
    def has_status(self, status):
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

    """
    A class representing a GTFS (General Transit Feed Specification) schedule source.

    This class extends the Source base class and provides specific attributes and methods
    for managing GTFS schedule data sources. It includes additional information such as
    geographic location, bounding box coordinates, and GTFS-specific URLs.

    Attributes:
        country_code (str): The country code where the GTFS data is applicable.
        subdivision_name (str, optional): The name of the subdivision (e.g., state, province).
        municipality (str, optional): The name of the municipality.
        bbox_min_lat (float): Minimum latitude of the bounding box.
        bbox_max_lat (float): Maximum latitude of the bounding box.
        bbox_min_lon (float): Minimum longitude of the bounding box.
        bbox_max_lon (float): Maximum longitude of the bounding box.
        bbox_extracted_on (str): Date when the bounding box was extracted.
        latest_url (str): URL for the latest version of the GTFS data.
        feed_contact_email (str, optional): Contact email for the GTFS feed.
        redirects (list): List of redirect URLs, if any.

    Note:
        This class inherits attributes from the Source base class, including
        mdb_source_id, data_type, provider, name, etc.
    """

    def __init__(self, **kwargs):
        """
        Initialize a GtfsScheduleSource instance.

        This method extends the parent class initializer and sets additional
        attributes specific to GTFS schedule sources.

        Args:
            **kwargs: Keyword arguments containing the source's attributes.
                Expected keys include LOCATION, URLS, FEED_CONTACT_EMAIL, and REDIRECTS,
                in addition to those required by the parent Source class.

        Note:
            The LOCATION dictionary is expected to contain COUNTRY_CODE, SUBDIVISION_NAME,
            MUNICIPALITY, and BOUNDING_BOX information.
        """
        super().__init__(**kwargs)
        location = kwargs.pop(LOCATION, {})
        self.country_code = location.pop(COUNTRY_CODE)
        self.subdivision_name = location.pop(SUBDIVISION_NAME, None)
        self.municipality = location.pop(MUNICIPALITY, None)
        bounding_box = location.pop(BOUNDING_BOX, {})
        self.bbox_min_lat = bounding_box.pop(MINIMUM_LATITUDE)
        self.bbox_max_lat = bounding_box.pop(MAXIMUM_LATITUDE)
        self.bbox_min_lon = bounding_box.pop(MINIMUM_LONGITUDE)
        self.bbox_max_lon = bounding_box.pop(MAXIMUM_LONGITUDE)
        self.bbox_extracted_on = bounding_box.pop(EXTRACTED_ON)
        urls = kwargs.pop(URLS, {})
        self.latest_url = urls.pop(LATEST)
        self.feed_contact_email = kwargs.pop(FEED_CONTACT_EMAIL, None)
        self.redirects = kwargs.pop(REDIRECTS, [])

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
            DIRECT_DOWNLOAD: self.direct_download_url,
            AUTHENTICATION_TYPE: self.authentication_type,
            AUTHENTICATION_INFO: self.authentication_info_url,
            API_KEY_PARAMETER_NAME: self.api_key_parameter_name,
            LATEST: self.latest_url,
            LICENSE: self.license_url,
            FEATURES: self.features,
            STATUS: self.status,
            FEED_CONTACT_EMAIL: self.feed_contact_email,
            REDIRECTS: self.redirects,
        }
        return json.dumps(self.schematize(**attributes), ensure_ascii=False)

    def __repr__(self):
        return f"GtfsScheduleSource({self.__str__()})"

    def has_subdivision_name(self, subdivision_name):
        return self.subdivision_name == subdivision_name

    def has_country_code(self, country_code):
        return self.country_code == country_code

    def has_feature(self, feature):
        return feature in self.features if self.features is not None else False

    def has_status(self, status):
        return self.status == status or (self.status is None and status == ACTIVE)

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
        # Update the authentication-related fields first
        authentication_type = kwargs.get(AUTHENTICATION_TYPE)
        if authentication_type is not None:
            self.authentication_type = authentication_type
        authentication_info_url = kwargs.get(AUTHENTICATION_INFO)
        if authentication_info_url is not None:
            self.authentication_info_url = authentication_info_url
        api_key_parameter_name = kwargs.get(API_KEY_PARAMETER_NAME)
        if api_key_parameter_name is not None:
            self.api_key_parameter_name = api_key_parameter_name

        # Update the fields requiring the direct download URL
        direct_download_url = kwargs.get(DIRECT_DOWNLOAD)
        api_key_parameter_value = kwargs.get(API_KEY_PARAMETER_VALUE)
        if direct_download_url is not None:
            dataset_path = download_dataset(
                url=direct_download_url,
                authentication_type=authentication_type,
                api_key_parameter_name=api_key_parameter_name,
                api_key_parameter_value=api_key_parameter_value,
            )
            if is_readable(file_path=dataset_path, load_func=load_gtfs):
                self.direct_download_url = direct_download_url
                (
                    self.bbox_min_lat,
                    self.bbox_max_lat,
                    self.bbox_min_lon,
                    self.bbox_max_lon,
                ) = extract_gtfs_bounding_box(file_path=dataset_path)
                self.bbox_extracted_on = get_iso_time()
            # Delete the downloaded dataset because we don't need it anymore
            os.remove(dataset_path)

        # Update the other fields
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
        features = kwargs.get(FEATURES)
        if features is not None:
            self.features = features
        status = kwargs.get(STATUS)
        if status is not None:
            self.status = status
        feed_contact_email = kwargs.get(FEED_CONTACT_EMAIL)
        if feed_contact_email is not None:
            self.feed_contact_email = feed_contact_email

        # Update the redirects
        redirects = kwargs.get(REDIRECTS)
        if redirects is not None:
            self.redirects = [
                {
                    REDIRECT_ID: elem.get(REDIRECT_ID), REDIRECT_COMMENT: elem.get(REDIRECT_COMMENT)
                 } for elem in redirects
            ]
            self.redirects = list(filter(lambda x: x.get(REDIRECT_ID) is not None, self.redirects))
        return self

    @classmethod
    def build(cls, **kwargs):
        instance = None
        direct_download_url = kwargs.get(DIRECT_DOWNLOAD)
        authentication_type = kwargs.get(AUTHENTICATION_TYPE)
        api_key_parameter_name = kwargs.get(API_KEY_PARAMETER_NAME)
        api_key_parameter_value = kwargs.get(API_KEY_PARAMETER_VALUE)
        dataset_path = download_dataset(
            direct_download_url,
            authentication_type,
            api_key_parameter_name,
            api_key_parameter_value,
        )
        if is_readable(file_path=dataset_path, load_func=load_gtfs):
            data_type = GTFS
            (
                minimum_latitude,
                maximum_latitude,
                minimum_longitude,
                maximum_longitude,
            ) = extract_gtfs_bounding_box(file_path=dataset_path)
            extracted_on = get_iso_time()

            # Delete the downloaded dataset because we don't need it anymore
            os.remove(dataset_path)

            subdivision_name = kwargs.get(SUBDIVISION_NAME)
            subdivision_name = (
                subdivision_name if subdivision_name is not None else UNKNOWN
            )
            filename = create_filename(
                country_code=kwargs.get(COUNTRY_CODE),
                subdivision_name=subdivision_name,
                provider=kwargs.get(PROVIDER),
                data_type=data_type,
                mdb_source_id=kwargs.get(MDB_SOURCE_ID),
                extension=JSON,
            )
            latest = create_latest_url(
                country_code=kwargs.get(COUNTRY_CODE),
                subdivision_name=subdivision_name,
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
            FEED_CONTACT_EMAIL: kwargs.pop(FEED_CONTACT_EMAIL, None),
            FEATURES: kwargs.pop(FEATURES, None),
            STATUS: kwargs.pop(STATUS, None),
            LOCATION: {
                COUNTRY_CODE: kwargs.pop(COUNTRY_CODE),
                SUBDIVISION_NAME: kwargs.pop(SUBDIVISION_NAME, None),
                MUNICIPALITY: kwargs.pop(MUNICIPALITY, None),
                BOUNDING_BOX: {
                    MINIMUM_LATITUDE: kwargs.pop(MINIMUM_LATITUDE),
                    MAXIMUM_LATITUDE: kwargs.pop(MAXIMUM_LATITUDE),
                    MINIMUM_LONGITUDE: kwargs.pop(MINIMUM_LONGITUDE),
                    MAXIMUM_LONGITUDE: kwargs.pop(MAXIMUM_LONGITUDE),
                    EXTRACTED_ON: kwargs.pop(EXTRACTED_ON),
                },
            },
            URLS: {
                DIRECT_DOWNLOAD: kwargs.pop(DIRECT_DOWNLOAD),
                AUTHENTICATION_TYPE: kwargs.pop(AUTHENTICATION_TYPE, None),
                AUTHENTICATION_INFO: kwargs.pop(AUTHENTICATION_INFO, None),
                API_KEY_PARAMETER_NAME: kwargs.pop(API_KEY_PARAMETER_NAME, None),
                LATEST: kwargs.pop(LATEST),
                LICENSE: kwargs.pop(LICENSE, None),
            },
            REDIRECTS: kwargs.pop(REDIRECTS, None),
        }
        if schema[NAME] is None:
            del schema[NAME]
        if schema[URLS][AUTHENTICATION_TYPE] is None:
            del schema[URLS][AUTHENTICATION_TYPE]
        if schema[URLS][AUTHENTICATION_INFO] is None:
            del schema[URLS][AUTHENTICATION_INFO]
        if schema[URLS][API_KEY_PARAMETER_NAME] is None:
            del schema[URLS][API_KEY_PARAMETER_NAME]
        if schema[URLS][LICENSE] is None:
            del schema[URLS][LICENSE]
        if schema[LOCATION][SUBDIVISION_NAME] is None:
            del schema[LOCATION][SUBDIVISION_NAME]
        if schema[LOCATION][MUNICIPALITY] is None:
            del schema[LOCATION][MUNICIPALITY]
        if schema[FEATURES] is None:
            del schema[FEATURES]
        if schema[STATUS] is None:
            del schema[STATUS]
        if schema[FEED_CONTACT_EMAIL] is None:
            del schema[FEED_CONTACT_EMAIL]
        if schema[REDIRECTS] is None:
            del schema[REDIRECTS]
        return schema


class GtfsRealtimeSource(Source):

    """
    A class representing a GTFS (General Transit Feed Specification) realtime source.

    This class extends the Source base class and provides specific attributes and methods
    for managing GTFS realtime data sources. It includes additional information such as
    the entity type of the realtime data and references to related static GTFS data.

    Attributes:
        static_catalog (GtfsScheduleSourcesCatalog): A catalog of GTFS schedule sources,
            shared across all instances of this class.
        entity_type (str): The type of entity this realtime source represents 
            (e.g., 'vehicle positions', 'trip updates', 'service alerts').
        static_reference (str, optional): A reference to the related static GTFS data source.
        note (str, optional): Additional notes or comments about this realtime source.

    Note:
        This class inherits attributes from the Source base class, including
        mdb_source_id, data_type, provider, name, etc.
    """

    static_catalog = GtfsScheduleSourcesCatalog()

    def __init__(self, **kwargs):
        """
        Initialize a GtfsRealtimeSource instance.

        This method extends the parent class initializer and sets additional
        attributes specific to GTFS realtime sources.

        Args:
            **kwargs: Keyword arguments containing the source's attributes.
                Expected keys include ENTITY_TYPE, STATIC_REFERENCE, and NOTE,
                in addition to those required by the parent Source class.

        Raises:
            KeyError: If the required ENTITY_TYPE key is not provided in kwargs.
        """
        super().__init__(**kwargs)
        self.entity_type = kwargs.pop(ENTITY_TYPE)
        self.static_reference = kwargs.pop(STATIC_REFERENCE, None)
        self.note = kwargs.pop(NOTE, None)

    def __str__(self):
        attributes = {
            MDB_SOURCE_ID: self.mdb_source_id,
            DATA_TYPE: self.data_type,
            ENTITY_TYPE: self.entity_type,
            PROVIDER: self.provider,
            NAME: self.name,
            STATIC_REFERENCE: self.static_reference,
            NOTE: self.note,
            DIRECT_DOWNLOAD: self.direct_download_url,
            AUTHENTICATION_TYPE: self.authentication_type,
            AUTHENTICATION_INFO: self.authentication_info_url,
            API_KEY_PARAMETER_NAME: self.api_key_parameter_name,
            LICENSE: self.license_url,
            FEATURES: self.features,
            STATUS: self.status,
        }
        return json.dumps(self.schematize(**attributes), ensure_ascii=False)

    def __repr__(self):
        return f"GtfsRealtimeSource({self.__str__()})"

    @classmethod
    def get_static_sources(cls, static_reference):
        static_sources = []
        if static_reference is not None:
            static_sources = [
                cls.static_catalog.get_source(source_id)
                for source_id in static_reference
            ]
        return static_sources

    def has_subdivision_name(self, subdivision_name):
        static_sources = self.get_static_sources(self.static_reference)
        return any(
            static_source.subdivision_name == subdivision_name
            for static_source in static_sources
        )

    def has_country_code(self, country_code):
        static_sources = self.get_static_sources(self.static_reference)
        return any(
            static_source.country_code == country_code
            for static_source in static_sources
        )

    def has_feature(self, feature):
        static_sources = self.get_static_sources(self.static_reference)
        in_static_source = any(
            [
                feature in static_source.features
                if static_source.features is not None
                else False
                for static_source in static_sources
            ]
        )
        in_realtime_source = (
            feature in self.features if self.features is not None else False
        )
        return in_static_source or in_realtime_source

    def has_status(self, status):
        return self.status == status or (self.status is None and status == ACTIVE)

    def is_overlapping_bounding_box(
        self, minimum_latitude, maximum_latitude, minimum_longitude, maximum_longitude
    ):
        static_sources = self.get_static_sources(self.static_reference)
        return any(
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
            for static_source in static_sources
        )

    def has_latest_dataset(self):
        return False

    def update(self, **kwargs):
        entity_type = kwargs.get(ENTITY_TYPE)
        if entity_type is not None:
            self.entity_type = entity_type
        provider = kwargs.get(PROVIDER)
        if provider is not None:
            self.provider = provider
        name = kwargs.get(NAME)
        if name is not None:
            self.name = name
        static_reference = kwargs.get(STATIC_REFERENCE)
        if static_reference is not None:
            self.static_reference = static_reference
        note = kwargs.get(NOTE)
        if note is not None:
            self.note = note
        direct_download_url = kwargs.get(DIRECT_DOWNLOAD)
        if direct_download_url is not None:
            self.direct_download_url = direct_download_url
        authentication_type = kwargs.get(AUTHENTICATION_TYPE)
        if authentication_type is not None:
            self.authentication_type = authentication_type
        authentication_info_url = kwargs.get(AUTHENTICATION_INFO)
        if authentication_info_url is not None:
            self.authentication_info_url = authentication_info_url
        api_key_parameter_name = kwargs.get(API_KEY_PARAMETER_NAME)
        if api_key_parameter_name is not None:
            self.api_key_parameter_name = api_key_parameter_name
        license_url = kwargs.get(LICENSE)
        if license_url is not None:
            self.license_url = license_url
        features = kwargs.get(FEATURES)
        if features is not None:
            self.features = features
        status = kwargs.get(STATUS)
        if status is not None:
            self.status = status
        return self

    @classmethod
    def build(cls, **kwargs):
        data_type = GTFS_RT
        static_reference = kwargs.get(STATIC_REFERENCE)
        static_sources = cls.get_static_sources(static_reference)
        country_code = (
            static_sources[0].country_code if len(static_sources) > 0 else UNKNOWN
        )
        optional_subdivision_name = (
            static_sources[0].subdivision_name if len(static_sources) > 0 else UNKNOWN
        )
        subdivision_name = (
            optional_subdivision_name
            if optional_subdivision_name is not None
            else UNKNOWN
        )

        filename_provider = kwargs.get(PROVIDER)
        name = kwargs.get(NAME)
        if name is not None:
            filename_provider = name
        filename_data_type = "-".join(
            [data_type] + [e_type for e_type in kwargs.get(ENTITY_TYPE)]
        )
        filename = create_filename(
            country_code=country_code,
            subdivision_name=subdivision_name,
            provider=filename_provider,
            data_type=filename_data_type,
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
            ENTITY_TYPE: kwargs.pop(ENTITY_TYPE),
            PROVIDER: kwargs.pop(PROVIDER),
            NAME: kwargs.pop(NAME, None),
            STATIC_REFERENCE: kwargs.pop(STATIC_REFERENCE, None),
            NOTE: kwargs.pop(NOTE, None),
            FEATURES: kwargs.pop(FEATURES, None),
            STATUS: kwargs.pop(STATUS, None),
            URLS: {
                DIRECT_DOWNLOAD: kwargs.pop(DIRECT_DOWNLOAD),
                AUTHENTICATION_TYPE: kwargs.pop(AUTHENTICATION_TYPE, None),
                AUTHENTICATION_INFO: kwargs.pop(AUTHENTICATION_INFO, None),
                API_KEY_PARAMETER_NAME: kwargs.pop(API_KEY_PARAMETER_NAME, None),
                LICENSE: kwargs.pop(LICENSE, None),
            },
        }
        if schema[NAME] is None:
            del schema[NAME]
        if schema[NOTE] is None:
            del schema[NOTE]
        if schema[STATIC_REFERENCE] is None:
            del schema[STATIC_REFERENCE]
        if schema[URLS][AUTHENTICATION_TYPE] is None:
            del schema[URLS][AUTHENTICATION_TYPE]
        if schema[URLS][AUTHENTICATION_INFO] is None:
            del schema[URLS][AUTHENTICATION_INFO]
        if schema[URLS][API_KEY_PARAMETER_NAME] is None:
            del schema[URLS][API_KEY_PARAMETER_NAME]
        if schema[URLS][LICENSE] is None:
            del schema[URLS][LICENSE]
        if schema[FEATURES] is None:
            del schema[FEATURES]
        if schema[STATUS] is None:
            del schema[STATUS]
        return schema
