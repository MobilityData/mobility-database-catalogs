import Foundation
#if canImport(FoundationNetworking)
    import FoundationNetworking
#endif

struct column {
    static let  fourZerothreeClientError : Int = 0 // A
    static let  timestamp                : Int = 1 // B
    static let  provider                 : Int = 2 // C
    static let  oldMobilityDatabaseID    : Int = 3 // D
    static let  datatype                 : Int = 4 // E
    static let  issueType                : Int = 5 // F
    static let  downloadurl              : Int = 6 // G
    static let  country                  : Int = 7 // H
    static let  subdivision_name         : Int = 8 // I
    static let  municipality             : Int = 9 // J
    static let  name                     : Int = 10 // K
    static let  license_url              : Int = 11 // L
    static let  authentication_type      : Int = 12 // M
    static let  authentication_info_url  : Int = 13 // N
    static let  api_key_parameter_name   : Int = 14 // O
    static let  note                     : Int = 15 // P
    static let  status                   : Int = 16 // Q
    static let  redirects                : Int = 17 // R
    static let  dataproduceremail        : Int = 18 // S

    // List properties manually as a static array
    static var allStructs                : Int { return 19 }
}

struct feed {
    var fourZerothreeClientError : String // we ignore this column
    var timestamp                : String
    var provider                 : String
    var oldMobilityDatabaseID    : Int
    var dataType                 : DataType
    var dataTypeString           : String
    var issueType                : IssueType
    var downloadURL              : String
    var country                  : String
    var subdivisionName          : String
    var municipality             : String
    var name                     : String
    var licenseURL               : String
    var authenticationType       : Int
    var authenticationInfoURL    : String
    var apiKeyParameterName      : String
    var note                     : String
    var status                   : String
    var redirects                : String
    var dataProducerEmail        : String

    // Add count() function
    func count() -> Int { return Mirror(reflecting: self).children.count }

    /// Generates a list of real-time data codes based on the `dataTypeString` property.
    ///
    /// - Returns: An array of strings containing the corresponding real-time data codes.
    func realtimeCode() -> [String] {
        let returnArray: [String] = [
            realtimeEntityTypes.vehiclePositions,
            realtimeEntityTypes.tripUpdates,
            realtimeEntityTypes.serviceAlerts
        ].filter { dataTypeString.contains($0) }
        
        // Return the array, or a default array containing "tripUpdates" if empty
        return returnArray.isEmpty ? [realtimeEntityTypes.tripUpdates] : returnArray
    }

    /// Determines the authentication type based on a given authentication string, handling whitespace and invalid values.
    ///
    /// - Parameter authString: A potentially whitespace-padded string representing the authentication type.
    /// - Returns: An integer value representing the authentication type. If the string contains "0", "1", or "2" (with optional whitespace padding), it returns the respective integer. Defaults to `0` if the value does not match any specific type or if conversion fails.
    func authenticationType(for authString: String) -> Int {
        let trimmedAuthString : String = authString.trimmingCharacters(in: .whitespaces)
        return Int(trimmedAuthString) ?? 0
    }
}

struct defaults {
    static let date                      : String = "01/01/1970"
    static let toBeProvided              : String = "TO_BE_PROVIDED"
    static let emptyValue                : String = "\"\""
    static let emptyValueRaw             : String = ""
    static let csvLineSeparator          : String = "\n"
    static let csvColumnSeparator        : String = ","
}

struct issueTypeString {
    static let isAddNewFeed              : String = "New feed"
    static let isAddNewSource            : String = "New source"
    static let isUpdateExistingFeed      : String = "Source update"
    static let isFeedUpdate              : String = "Feed update"
    static let isToRemoveFeed            : String = "removed"
    static let unknown                   : String = "unknown"
}

struct dataTypeString {
    static let schedule                  : String = "Schedule"
    static let realtime                  : String = "Realtime"
}

enum IssueType {
    case isAddNewFeed, isFeedUpdate, isToRemoveFeed, unknown
}

enum DataType {
    case schedule, realtime, unknown
}

struct realtimeEntityTypesString {
    static let vehiclePositions          : String = "Vehicle Positions"
    static let tripUpdates               : String = "Trip Updates"
    static let serviceAlerts             : String = "Service Alerts"
    static let unknown                   : String = "general / unknown"
    static let empty                     : String = "nil"
}

struct realtimeEntityTypes {
    static let vehiclePositions          : String = "vp"
    static let tripUpdates               : String = "tu"
    static let serviceAlerts             : String = "sa"
    static let unknown                   : String = "gu"
    static let empty                     : String = "nil"
}

/// Determines the `IssueType` based on the provided string value.
/// - Parameter issueTypeValue: A `String` representing the issue type, which may contain certain keywords.
/// - Returns: An `IssueType` enum value based on the provided string. If no match is found, returns `.unknown`.
func issueType(for issueTypeValue: String) -> IssueType {
    let issueTypeMappings: [(IssueType, [String])] = [
        (.isAddNewFeed, [issueTypeString.isAddNewFeed, issueTypeString.isAddNewSource]),
        (.isFeedUpdate, [issueTypeString.isUpdateExistingFeed, issueTypeString.isFeedUpdate]),
        (.isToRemoveFeed, [issueTypeString.isToRemoveFeed])
    ]
    
    return issueTypeMappings.first { (_: IssueType, keywords : [String] ) in
        keywords.contains { issueTypeValue.contains($0) }
    }?.0 ?? .unknown
}

/// Determines the `DataType` based on the provided string value.
/// - Parameter dataTypeValue: A `String` representing the data type, which may contain certain keywords.
/// - Returns: A `DataType` enum value based on the provided string. If no match is found, returns `.unknown`.
func dataType(for dataTypeValue: String) -> DataType {
    let dataTypeMappings: [(DataType, [String])] = [
        (.schedule, [dataTypeString.schedule]),
        (.realtime, [dataTypeString.realtime, realtimeEntityTypesString.vehiclePositions, realtimeEntityTypesString.tripUpdates, realtimeEntityTypesString.serviceAlerts, realtimeEntityTypesString.unknown, realtimeEntityTypes.empty])
    ]
    
    return dataTypeMappings.first { (_: DataType, keywords : [String] ) in
        keywords.contains { dataTypeValue.contains($0) }
    }?.0 ?? .unknown
}

/// Parses an array of CSV lines into an array of `feed` instances.
/// - Parameters:
///   - csvLines: An array of strings, each representing a row from the CSV file.
///   - columnSeparator: A string used to separate columns within each row.
///   - dateFormatRegex: A regex pattern to match the date format in the CSV data.
///   - dateFormatDesired: A string representing the desired date format for output.
/// - Returns: An array of `feed` instances constructed from the CSV data.
func parseCSV(csvLines: [String], columnSeparator: String, dateFormatRegex: String, dateFormatDesired: String) -> [feed] {

    if isInDebugMode { print("\nprocessing CSV Array column...") }

    var feeds: [feed] = []
    var lastKnownProvider : String = defaults.toBeProvided
    let dateFormatAsRegex: Regex<AnyRegexOutput>? = try? Regex(dateFormatRegex)
    
    for line: String in csvLines {
        let csvArrayColumn : [String] = line.components(separatedBy: columnSeparator)
        guard csvArrayColumn.count >= column.allStructs else { continue } // Ensure there are enough columns

        // Get issue and data types
        let issueTypeValue : IssueType = issueType(for: csvArrayColumn[column.issueType].trimmingCharacters(in: .whitespacesAndNewlines))
        let dataTypeValue  : DataType  = dataType(for: csvArrayColumn[column.datatype].count < 3 ? realtimeEntityTypes.empty : csvArrayColumn[column.datatype])

        // Format timestamp properly
        let timestampFormatted : String = extractDate(from: csvArrayColumn[column.timestamp].trimmingCharacters(in: .whitespacesAndNewlines), usingGREP: dateFormatAsRegex!, desiredDateFormat: dateFormatDesired)

        // Check if provider is empty, suggest last known if true.
        var provider: String = csvArrayColumn[column.provider].trimmingCharacters(in: .whitespacesAndNewlines)
        if provider.count > 0 { lastKnownProvider = provider } ; provider = provider.isEmpty ? "\(defaults.toBeProvided) (\(lastKnownProvider) ?)" : provider

        // Check if download URL is valid
        var downloadURLvalue : String = csvArrayColumn[column.downloadurl].trimmingCharacters(in: .whitespacesAndNewlines)
        if !(isURLPresent(in: downloadURLvalue) && downloadURLvalue.count < 4) { downloadURLvalue = defaults.emptyValue }

        // Check if license URL is valid
        var licenseURLvalue : String = csvArrayColumn[column.license_url].trimmingCharacters(in: .whitespacesAndNewlines)
        if !(isURLPresent(in: licenseURLvalue) && licenseURLvalue.count > 0) { licenseURLvalue = defaults.emptyValue }

        // Get authentification Int
        let authTypeValue : Int = authenticationType(for: csvArrayColumn[column.authentication_type].trimmingCharacters(in: .whitespacesAndNewlines))

        let newFeed : feed = feed (
            fourZerothreeClientError    : csvArrayColumn[column.fourZerothreeClientError],
            timestamp                   : timestampFormatted,
            provider                    : provider,
            oldMobilityDatabaseID       : Int(csvArrayColumn[column.oldMobilityDatabaseID].trimmingCharacters(in: .escapedDoubleQuote)) ?? 0,
            dataType                    : dataTypeValue,
            dataTypeString              : csvArrayColumn[column.datatype].count < 3 ? realtimeEntityTypes.empty : csvArrayColumn[column.datatype],
            issueType                   : issueTypeValue,
            downloadURL                 : downloadURLvalue,
            country                     : csvArrayColumn[column.country].trimmingCharacters(in: .whitespacesAndNewlines),
            subdivisionName             : csvArrayColumn[column.subdivision_name].trimmingCharacters(in: .whitespacesAndNewlines),
            municipality                : csvArrayColumn[column.municipality].trimmingCharacters(in: .whitespacesAndNewlines),
            name                        : csvArrayColumn[column.name].trimmingCharacters(in: .whitespacesAndNewlines),
            licenseURL                  : licenseURLvalue,
            authenticationType          : authTypeValue,
            authenticationInfoURL       : csvArrayColumn[column.authentication_info_url].trimmingCharacters(in: .whitespacesAndNewlines),
            apiKeyParameterName         : csvArrayColumn[column.api_key_parameter_name].trimmingCharacters(in: .whitespacesAndNewlines),
            note                        : csvArrayColumn[column.note].trimmingCharacters(in: .whitespacesAndNewlines),
            status                      : csvArrayColumn[column.status].trimmingCharacters(in: .whitespacesAndNewlines),
            redirects                   : redirectArray(for: csvArrayColumn[column.redirects].trimmingCharacters(in: .whitespacesAndNewlines).trimmingCharacters(in: .escapedDoubleQuote)),
            dataProducerEmail           : csvArrayColumn[column.dataproduceremail].trimmingCharacters(in: .whitespacesAndNewlines)
        )
        
        feeds.append(newFeed)
    }
    
    return feeds
}

// Will be used to filter empty parameters from this script's output
let everyPythonScriptFunctionsParameterNames : [String] = ["provider=", "entity_type=", "country_code=", "authentication_type=", "authentication_info_url=", "api_key_parameter_name=", "subdivision_name=", "municipality=", "country_code=", "license_url=", "name=", "status=", "features=", "note=", "feed_contact_email=", "redirects="]

let argNames : [String] = CommandLine.arguments
// let argNames : [String] = ["scriptname", "https://docs.google.com/spreadsheets/d/1Q96KDppKsn2khdrkraZCQ7T_qRSfwj7WsvqXvuMt4Bc/gviz/tq?tqx=out:csv;outFileName:data&sheet=%5BCLEANED%5D%20For%20import", "11/11/2024", "[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2}", "MM/dd/yyyy"]

// Set to false for production use
let isInDebugMode : Bool = false

if argNames.count == 5 {
    
    let csvURLStringArg      : String = argNames[1] // the first argName  [0] is the name of the script, we can ignore in this context.
    let _                    : String = argNames[2] // Deprecated, we no longer look for a specific date.
    let dateFormatGREPArg    : String = argNames[3]
    let dateFormatDesiredArg : String = argNames[4]
    
    guard let csvURLasURL : URL = URL(string: csvURLStringArg) else {
        print("\n   ERROR: The specified URL does not appear to exist :\n   \(csvURLStringArg)\n")
        exit(1)
    }

    let csvData : String = try String(contentsOf: csvURLasURL, encoding:.utf8)
    var csvLines : [String] = csvData.components(separatedBy: defaults.csvLineSeparator) ; csvLines.removeFirst(1)
    let csvArray : [feed] = parseCSV(csvLines: csvLines, columnSeparator: defaults.csvColumnSeparator, dateFormatRegex: dateFormatGREPArg, dateFormatDesired: dateFormatDesiredArg)

    if isInDebugMode { print("\n\n\t\tcsvArray contains (\(csvArray.count) item(s)) :\n\n \(csvArray)\n") }
    
    var PYTHON_SCRIPT_OUTPUT : String = ""

    for currentFeed : feed in csvArray {

        var PYTHON_SCRIPT_ARGS_TEMP : String = ""
        if isInDebugMode { print("\t\tcolumn count / all cases count : \(currentFeed.count()) / \(column.allStructs)\n\t\tissue    : \(currentFeed.issueType)\n\t\tdatatype : \(currentFeed.dataType)") }
        if isInDebugMode { print("\t\redirects : \(currentFeed.redirects)") }
        if isInDebugMode { print("\t\tdownload URL || licence URL : \(currentFeed.downloadURL) || \(currentFeed.licenseURL)") }

        if currentFeed.issueType == IssueType.isAddNewFeed {

            if isInDebugMode { print("\t\t\tCurrent feed is new.") }

            if currentFeed.dataType == DataType.schedule { // add_gtfs_schedule_source

                PYTHON_SCRIPT_ARGS_TEMP  = """
                add_gtfs_schedule_source(
                provider=\"\(currentFeed.provider)\", 
                country_code=\"\(currentFeed.country)\", 
                direct_download_url=\"\(currentFeed.downloadURL)\", 
                authentication_type=\(currentFeed.authenticationType), 
                authentication_info_url=\"\(currentFeed.authenticationInfoURL)\", 
                api_key_parameter_name=\"\(currentFeed.apiKeyParameterName)\", 
                subdivision_name=\"\(currentFeed.subdivisionName)\", 
                municipality=\"\(currentFeed.municipality)\", 
                license_url=\"\(currentFeed.licenseURL)\", 
                name=\"\(currentFeed.name)\", 
                status=\"\(currentFeed.status)\", 
                feed_contact_email=\"\(currentFeed.dataProducerEmail)\"
                \(currentFeed.redirects))
                """

            } else if currentFeed.dataType == DataType.realtime {  // add_gtfs_realtime_source
                
                PYTHON_SCRIPT_ARGS_TEMP = """
                add_gtfs_realtime_source(
                entity_type=[\"\(currentFeed.realtimeCode().joined(separator:"\", \""))\"], 
                provider=\"\(currentFeed.provider)\", 
                direct_download_url=\"\(currentFeed.downloadURL)\", 
                authentication_type=\(currentFeed.authenticationType), 
                authentication_info_url=\"\(currentFeed.authenticationInfoURL)\", 
                api_key_parameter_name=\"\(currentFeed.apiKeyParameterName)\", 
                license_url=\"\(currentFeed.licenseURL)\", 
                name=\"\(currentFeed.name)\", 
                note=\"\(currentFeed.note)\", 
                status=\"\(currentFeed.status)\", 
                feed_contact_email=\"\(currentFeed.dataProducerEmail)\"
                \(currentFeed.redirects))
                """

            }

        } else if currentFeed.issueType == IssueType.isFeedUpdate {

            if isInDebugMode { print("\t\t\tCurrent feed is update.") }

            if currentFeed.dataType == DataType.schedule { // update_gtfs_schedule_source

                PYTHON_SCRIPT_ARGS_TEMP = """
                update_gtfs_schedule_source(mdb_source_id=\(currentFeed.oldMobilityDatabaseID), 
                provider=\"\(currentFeed.provider)\", 
                name=\"\(currentFeed.name)\", 
                country_code=\"\(currentFeed.country)\", 
                subdivision_name=\"\(currentFeed.subdivisionName)\", 
                municipality=\"\(currentFeed.municipality)\", 
                authentication_type=\(currentFeed.authenticationType), 
                authentication_info_url=\"\(currentFeed.authenticationInfoURL)\", 
                api_key_parameter_name=\"\(currentFeed.apiKeyParameterName)\", 
                status=\"\(currentFeed.status)\", 
                feed_contact_email=\"\(currentFeed.dataProducerEmail)\"
                \(currentFeed.redirects))
                """

            } else if currentFeed.dataType == DataType.realtime {  // update_gtfs_realtime_source
                
                PYTHON_SCRIPT_ARGS_TEMP = """
                update_gtfs_realtime_source(
                mdb_source_id=\(currentFeed.oldMobilityDatabaseID), 
                entity_type=[\"\(currentFeed.realtimeCode().joined(separator:"\", \""))\"], 
                provider=\"\(currentFeed.provider)\", 
                authentication_type=\(currentFeed.authenticationType), 
                authentication_info_url=\"\(currentFeed.authenticationInfoURL)\", 
                api_key_parameter_name=\"\(currentFeed.apiKeyParameterName)\", 
                name=\"\(currentFeed.name)\", 
                note=\"\(currentFeed.note)\", 
                status=\"\(currentFeed.status)\", 
                feed_contact_email=\"\(currentFeed.dataProducerEmail)\"
                \(currentFeed.redirects))
                """

            }

        } else if currentFeed.issueType == IssueType.isToRemoveFeed {

            if isInDebugMode { print("\t\t\tCurrent feed is to be removed.") }

            if currentFeed.dataType == DataType.schedule { // update_gtfs_schedule_source

                PYTHON_SCRIPT_ARGS_TEMP = """
                update_gtfs_schedule_source(
                mdb_source_id=\(currentFeed.oldMobilityDatabaseID), 
                provider=\"\(currentFeed.provider)\", 
                name=\"\"**** issued for removal ****\"\", 
                country_code=\"\(currentFeed.country)\", 
                subdivision_name=\"\(currentFeed.subdivisionName)\", 
                municipality=\"\(currentFeed.municipality)\", 
                authentication_type=\(currentFeed.authenticationType), 
                authentication_info_url=\"\(currentFeed.authenticationInfoURL)\", 
                api_key_parameter_name=\"\(currentFeed.apiKeyParameterName)\", 
                status=\"\(currentFeed.status)\", 
                feed_contact_email=\"\(currentFeed.dataProducerEmail)\"
                \(currentFeed.redirects))
                """


            } else if currentFeed.dataType == DataType.realtime {  // update_gtfs_realtime_source

                PYTHON_SCRIPT_ARGS_TEMP = """
                update_gtfs_realtime_source(
                mdb_source_id=\(currentFeed.oldMobilityDatabaseID), 
                entity_type=\"[\(currentFeed.realtimeCode().joined(separator:"\", \""))]\", 
                provider=\"\(currentFeed.provider)\", 
                authentication_type=\(currentFeed.authenticationType), 
                authentication_info_url=\"\(currentFeed.authenticationInfoURL)\", 
                api_key_parameter_name=\"\(currentFeed.apiKeyParameterName)\", 
                name=\"\"**** issued for removal ****\"\", 
                note=\"\(currentFeed.note)\", 
                status=\"\(currentFeed.status)\", 
                feed_contact_email=\"\(currentFeed.dataProducerEmail)\"
                \(currentFeed.redirects))
                """

            }

        } else if currentFeed.issueType == IssueType.unknown { // assume default is .isAddNewFeed

            if isInDebugMode { print("\t\t\tCurrent feed is assumed to be new.") }

            if currentFeed.dataType == DataType.schedule { // add_gtfs_schedule_source

                PYTHON_SCRIPT_ARGS_TEMP  = """
                add_gtfs_schedule_source(
                provider=\"\(currentFeed.provider)\", 
                country_code=\"\(currentFeed.country)\", 
                direct_download_url=\"\(currentFeed.downloadURL)\", 
                authentication_type=\(currentFeed.authenticationType), 
                authentication_info_url=\"\(currentFeed.authenticationInfoURL)\", 
                api_key_parameter_name=\"\(currentFeed.apiKeyParameterName)\", 
                subdivision_name=\"\(currentFeed.subdivisionName)\", 
                municipality=\"\(currentFeed.municipality)\", 
                license_url=\"\(currentFeed.licenseURL)\", 
                name=\"\(currentFeed.name)\", 
                status=\"\(currentFeed.status)\", 
                feed_contact_email=\"\(currentFeed.dataProducerEmail)\"
                \(currentFeed.redirects))
                """

            } else if currentFeed.dataType == DataType.realtime {  // add_gtfs_realtime_source

                PYTHON_SCRIPT_ARGS_TEMP = """
                add_gtfs_realtime_source(
                entity_type=\"[\(currentFeed.realtimeCode().joined(separator:"\", \""))]\", 
                provider=\"\(currentFeed.provider)\", 
                direct_download_url=\"\(currentFeed.downloadURL)\", 
                authentication_type=\(currentFeed.authenticationType), 
                authentication_info_url=\"\(currentFeed.authenticationInfoURL)\", 
                api_key_parameter_name=\"\(currentFeed.apiKeyParameterName)\", 
                license_url=\"\(currentFeed.licenseURL)\", 
                name=\"\(currentFeed.name)\", 
                note=\"\(currentFeed.note)\", 
                status=\"\(currentFeed.status)\", 
                feed_contact_email=\"\(currentFeed.dataProducerEmail)\"
                \(currentFeed.redirects))
                """

            }

        }

        // Let's remove the added newline characters
        PYTHON_SCRIPT_ARGS_TEMP = PYTHON_SCRIPT_ARGS_TEMP.replacingOccurrences(of: "\n", with: "")
        
        if isInDebugMode { print("\t\tPython script arg TEMP : \(PYTHON_SCRIPT_ARGS_TEMP)")}
        
        if PYTHON_SCRIPT_ARGS_TEMP.count > 0 { PYTHON_SCRIPT_OUTPUT = ( PYTHON_SCRIPT_OUTPUT + "§" + PYTHON_SCRIPT_ARGS_TEMP ) }
        
    } // END FOR LOOP

    // Replace single quotes (like in McGill's) with an apostrophe so there is no interference with the bash script in the next step.
    PYTHON_SCRIPT_OUTPUT = PYTHON_SCRIPT_OUTPUT.replacingOccurrences(of: "'", with: "ʼ")
    // Note: do not try to fix the ouput of multiple quotes (ex.: """") as it will break the python script.
    
    // Remove empty paramters from script output
    PYTHON_SCRIPT_OUTPUT = removeEmptyPythonParameters(in: PYTHON_SCRIPT_OUTPUT)
    
    // return final output so the action can grab it and pass it on to the Python script.
    if isInDebugMode { print("FINAL OUTPUT:") }
    print(PYTHON_SCRIPT_OUTPUT.dropFirst())
    
} else {
    print("Incorrect number of arguments provided to the script. Expected 4: a string with the URL, the date to find, a date format and the date format desired.")
    exit(1)
}

// MARK: - FUNCTIONS

/// Extracts a date from a string and formats it according to a desired format.
///
/// - Parameters:
///   - theDateToConvert: The string containing the date to be extracted.
///   - dateFormatAsGREP: A regular expression object defining the format of the date in the input string. This uses Apple's `Regex` type for pattern matching.
///   - desiredDateFormat: The desired format for the extracted date. This follows the standard `DateFormatter` format string syntax (e.g., "yyyy-MM-dd").
/// - Returns:
///   A String containing the extracted and formatted date string. If no match is found or the formatting fails, it returns the default date string (implementation detail referenced by `defaults.date`).
///
/// This function attempts to extract a date from the provided string using the specified regular expression.
///   - If a match is found, it extracts the matched substring and attempts to convert it to a `Date` object using the desired format string.
///   - If the conversion is successful, the function formats the `Date` object using the desired format and returns the resulting string.
///   - If no match is found or the conversion fails, the function returns the default date string.
///
/// - Note: The `defaults.date` property is not explicitly defined here. It's assumed to be a way to access a default date string used in case of errors. Consider clarifying its source and purpose in the actual implementation.
func extractDate(from theDateToConvert: String, usingGREP dateFormatAsGREP: Regex<AnyRegexOutput>, desiredDateFormat desiredFormat: String) -> String {
    if let match : Regex<Regex<AnyRegexOutput>.RegexOutput>.Match = theDateToConvert.firstMatch(of: dateFormatAsGREP) { 
        // find first match
        let matchOutput : String = String(match.output[0].substring!)

        // date formatter and find date
        let dateFormatter : DateFormatter = DateFormatter()
        dateFormatter.dateFormat = desiredFormat
        let date : Date? = dateFormatter.date(from: matchOutput)
        
        // default date if formatter fails, otherwise return correctly formatted date
        var returnDate : String = defaults.date
        if date != nil { returnDate = dateFormatter.string(from: date!) }
        return returnDate
    }
    
    // return default date
    return defaults.date
}

/// Generates a Python-like array inside a string from a comma-separated input string.
///
/// This function takes a raw input string, splits it by commas, and formats each
/// element into a specific JSON-like structure with `id` and `comment` keys.
/// If the input string is empty, it returns a default empty value.
///
/// - Parameter rawData: A comma-separated string of values to be formatted.
/// - Returns: A Python-like array inside a string representating the input values, or a default empty value if the input is empty.
///
/// - Note: The default empty value is provided by `defaults.emptyValue`.
func redirectArray(for rawData: String) -> String {
    if rawData.count > 0 {
        let argName   : String = ", redirects=["
        let closingSuffix : String = "]"
        let prefix    : String = "{\"\"id\"\": "
        let suffix    : String = ", \"\"comment\"\": \"\" \"\"}"
        let keyValuePairsJoiner : String = ", "

        let rawDataAsArray : [String] = rawData.components(separatedBy: ",")
        var valueKeyPairs : [String] = []

        for currentString : String in rawDataAsArray {
            valueKeyPairs.append(prefix + currentString + suffix)
        }

        let returnString : String = "\(argName)\(valueKeyPairs.joined(separator: keyValuePairsJoiner))\(closingSuffix)" // Ex.: , redirects=[{"id": 2036, "comment": ""}, {"id": 2037, "comment": ""}]    AKA a Python array of dicts
        return returnString
    }

    return defaults.emptyValueRaw
}

/// Determines the authentication type based on a given authentication string, handling whitespace and invalid values.
///
/// - Parameter authString: A potentially whitespace-padded string representing the authentication type.
/// - Returns: An integer value representing the authentication type. If the string contains "0", "1", or "2" (with optional whitespace padding), it returns the respective integer. Defaults to `0` if the value does not match any specific type or if conversion fails.
///
/// This function trims whitespace from `authString` and attempts to interpret it as an integer. If `authString` contains valid authentication types (0, 1, or 2), it returns the corresponding integer. Defaults to `0` if conversion fails.
func authenticationType(for authString: String) -> Int {
    let trimmedAuthString : String = authString.trimmingCharacters(in: .whitespaces)
    return Int(trimmedAuthString) ?? 0
}

/// Checks if a string contains a URL
///
/// - Parameter string: The string to search for a URL.
/// - Returns:
///   `true` if a URL is found in the string, otherwise `false`.
///
/// This function uses a regular expression to search for a valid URL pattern within the provided string. The supported URL format includes:
///   - http or https protocol
///   - Optional www subdomain
///   - Alphanumeric characters, hyphens, underscores, at signs, percent signs, periods, plus signs, tildes, and equal signs (up to 256 characters)
///   - Domain name with alphanumeric characters, parentheses, and periods (up to 6 characters)
///   - Optional path and query string components
func isURLPresent(in string: String) -> Bool {
    let pattern : String = #"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"#
    let range: Range<String.Index>? = string.range(of: pattern, options: .regularExpression)
    if range != nil { return true }
    return false
}

/// Removes empty parameter definitions from a Python script output string.
///
/// - Parameter outputString: The string containing the Python script output.
/// - Returns:
///   A new string with empty parameter definitions removed. The original string remains unmodified.
///
/// This function iterates through a predefined list of known Python script function parameter names (see `everyPythonScriptFunctionsParameterNames`).
///   - For each parameter name, it constructs two search strings:
///     - One targeting empty parameters with a comma before and triple quotes after the parameter name. (", parameterName"""")
///     - Another targeting empty parameters with the parameter name followed by triple quotes and a comma. (parameterName"""",)
///   - The function replaces all occurrences of these search strings with an empty string, effectively removing the empty parameter definitions.
///   - It iterates through all parameter names to handle potential occurrences of multiple empty parameters.
///
/// This function assumes `everyPythonScriptFunctionsParameterNames` is a constant containing a list of valid Python script function parameter names.
///   - Modifications to the original string are done on a copy to avoid unintended side effects.
func removeEmptyPythonParameters(in outputString: String) -> String {
    var returnString : String = outputString
    let comma : String = ","
    let doubleQuotes : String = "\"\"\"\""
    for currentParameter : String in everyPythonScriptFunctionsParameterNames {
        let stringToFindFirstPass  : String = "\(comma) \(currentParameter)\(doubleQuotes)"
        let stringToFindSecondPass : String = "\(currentParameter)\(doubleQuotes)\(comma) "
        returnString = returnString.replacingOccurrences(of: stringToFindFirstPass, with: "")
        returnString = returnString.replacingOccurrences(of: stringToFindSecondPass, with: "")
    }
    return returnString
}

extension CharacterSet {
    static let escapedDoubleQuote : CharacterSet = CharacterSet(charactersIn: "\"")
}