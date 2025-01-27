import Foundation
#if canImport(FoundationNetworking)
    import FoundationNetworking
#endif

// MARK: - ERRORS

enum ScriptError: Error {

    case noData
    case networkError
    case parseError
    case incorrectArgumentsCount
    case insufficientNumberOfColumns

    var description: String {
        switch self {
        case .noData:
            return "No data seems to be present in the source document."
        case .networkError:
            return "A network error occurred or the specified URL does not appear to exist."
        case .parseError:
            return "Failed to parse the CSV data."
        case .incorrectArgumentsCount:
            return "Incorrect number of arguments provided to the script. Expected 4: a string with the URL, the date to find, a date format and the date format desired."
        case .insufficientNumberOfColumns:
            return "Insufficient number of columns in the CSV."
        }
    }
}

// MARK: - DEFAULTS

struct defaults {
    static let date               : String = "01/01/1970"
    static let toBeProvided       : String = "TO_BE_PROVIDED"
    static let emptyValue         : String = "\"\""
    static let emptyValueRaw      : String = ""
    static let csvLineSeparator   : String = "\n"
    static let csvColumnSeparator : String = ","
    static let newline            : String = "\n"
    static let tab                : String = "\t"
    static let whitespace         : String = " "
    static let comma              : String = ","
    static let singleQuote        : String = "'"
    static let apostrophe         : String = "ʼ"
    static let doubleQuotes       : String = "\"\"\"\""
    static let finalOutputDivider : String = "§"

    static let httpAddressPattern : String = #"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"#
    static let everyPythonScriptFunctionsParameterNames: [String] = [
        "provider=", "entity_type=", "country_code=", "authentication_type=", "authentication_info_url=", "api_key_parameter_name=", "subdivision_name=",
        "municipality=", "license_url=", "name=", "status=", "features=", "note=", "feed_contact_email=", "redirects="
    ]
}

// MARK: - ENUMS

enum IssueType : String {
    case isAddNewFeed         = "New feed"
    case isFeedUpdate         = "Feed update"
    case isToRemoveFeed       = "removed"
    case isUnknown            = "unknown"
    case isAddNewSource       = "New source" // this is only used to match variations in wording that appeared over time
    case isUpdateExistingFeed = "Source update" // this is only used to match variations in wording that appeared over time

    /// Provides a String for each issue type case.
    var asString : String { self.rawValue }
}

enum DataType : String {
    case schedule = "Schedule"
    case realtime = "Realtime"
    case unknown  = "Unknown"

    /// Provides a String for each realtime entity type case.
    var asString : String { self.rawValue }
}

enum RealtimeEntityType : String, CaseIterable {
    case schedule         = "Schedule"
    case realtime         = "Realtime"
    case vehiclePositions = "vp"
    case tripUpdates      = "tu"
    case serviceAlerts    = "sa"
    case unknown          = "gu"
    case empty            = "nil"

    /// Provides a 2-letter String for each realtime entity type case.
    var asShortString : String { self.rawValue }

    /// Provides a detailed String for each realtime entity type case.
    var asString: String {
        switch self {
            case .schedule         : return "Schedule"
            case .realtime         : return "Realtime"
            case .vehiclePositions : return "Vehicle Positions"
            case .tripUpdates      : return "Trip Updates"
            case .serviceAlerts    : return "Service Alerts"
            case .unknown          : return "Unknown"
            case .empty            : return "Nil"
        }
    }

    static var allAsStrings: [String] {
        return [
            RealtimeEntityType.schedule.asString,
            RealtimeEntityType.realtime.asString,
            RealtimeEntityType.vehiclePositions.asString,
            RealtimeEntityType.tripUpdates.asString,
            RealtimeEntityType.serviceAlerts.asString
        ]
    }

    static var allAsEnum: [RealtimeEntityType] {
        return [
            RealtimeEntityType.realtime,
            RealtimeEntityType.vehiclePositions,
            RealtimeEntityType.tripUpdates,
            RealtimeEntityType.serviceAlerts
        ]
    }

    /// Returns an String of `asShortString` values for the provided value of `RealtimeEntityType`
    func realtimeCode() -> String {
        return "\"\(self.asShortString)\""
    }
}

// MARK: - STRUCTS

/// A structure that defines column indices for mobility data processing.
///
/// This struct provides a set of static constants representing column positions in a data structure, likely used for handling mobility or transportation-related information. Each constant maps to a specific zero-based index position in the underlying data.
///
/// - Note: The structure maintains a fixed count of 19 columns (0-18)
struct column {
    static let  fourZeroThreeClientError : Int = 0 // A
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

    static var count                     : Int { return 19 }
}

/// A structure representing a MobilityData feed entry.
///
/// This struct encapsulates all properties of a single feed, including metadata, geographic information, authentication details, and status information. It serves as a comprehensive data model for storing and managing mobility feed data.
struct feed {
    var fourZeroThreeClientError : String // we ignore this column
    var timestamp                : String
    var provider                 : String
    var oldMobilityDatabaseID    : Int
    var dataType                 : RealtimeEntityType
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

    func count() -> Int { return Mirror(reflecting: self).children.count }

    /// Determines the authentication type based on a given authentication string, handling whitespace and invalid values.
    ///
    /// - Parameter authString: A potentially whitespace-padded string representing the authentication type.
    /// - Returns: An integer value representing the authentication type. If the string contains "0", "1", or "2" (with optional whitespace padding), it returns the respective integer. Defaults to `0` if the value does not match any specific type or if conversion fails.
    func authenticationType(for authString: String) -> Int {
        let trimmedAuthString : String = authString.trimmingCharacters(in: .whitespaces)
        return Int(trimmedAuthString) ?? 0
    }
}

// MARK: - MAIN

var args : [String] = [""]
var isInDebugMode : Bool = false

if CommandLine.arguments.count == 5 {
    // this is for using inside the GitHub workflow only.
    args = CommandLine.arguments
} else {
    // this is for local testing only.
    print("Running locally.")
    args = ["scriptname", 
        "https://docs.google.com/spreadsheets/d/1Q96KDppKsn2khdrkraZCQ7T_qRSfwj7WsvqXvuMt4Bc/gviz/tq?tqx=out:csv;outFileName:data&sheet=%5BCLEANED%5D%20For%20import&range=A2:S", 
        "11/11/2024", 
        "[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2}", 
        "MM/dd/yyyy"
    ]
    isInDebugMode = true
    // Google Sheet: https://docs.google.com/spreadsheets/d/1Q96KDppKsn2khdrkraZCQ7T_qRSfwj7WsvqXvuMt4Bc/edit?gid=2061813733#gid=2061813733 
}

// RUN MAIN SCRIPT
main()

/// The `main` function serves as the entry point for the script. It performs the following tasks:
/// - Validates the number of input arguments.
/// - Downloads and parses a CSV file based on provided arguments.
/// - Generates Python commands for manipulating feed data.
/// - Handles and logs errors gracefully.
///
/// The function terminates with appropriate exit codes:
/// - `0` for success.
/// - Specific error codes (`1`, `2`, `255`) for various failure scenarios.
///
/// - Throws: `ScriptError` for specific error conditions like incorrect arguments or data parsing issues.
func main() {
    do {
        if args.count == 5 {
            
            let csvURLStringArg      : String = args[1] // the first openingPrefix  [0] is the name of the script, we can ignore in this context.
            let _                    : String = args[2] // Deprecated, we no longer look for a specific date.
            let dateFormatGREPArg    : String = args[3]
            let dateFormatDesiredArg : String = args[4]

            let csvArray : [feed] = try downloadAndParseCSV(fromURL: csvURLStringArg, dateFormatRegex: dateFormatGREPArg, dateFormatDesired: dateFormatDesiredArg)

            if isInDebugMode { print("\n\t\tTotal number of feeds parsed from the CSV: \(csvArray.count)\n\n\t\t---\n") }
            if isInDebugMode { let allDescriptions : String = csvArray.map { $0.description }.joined(separator: "\n\n\t\t---\n\n") ; print("\(allDescriptions)\n") }
            if isInDebugMode { print("\t\t---\n\n\t\tCreating Python commands...\n") }
            
            var PYTHON_SCRIPT_OUTPUT : String = ""

            for currentFeed : feed in csvArray {

                var PYTHON_SCRIPT_ARGS_TEMP : String = ""

                if currentFeed.issueType == IssueType.isAddNewFeed {

                    if isInDebugMode { print("\t\tCurrent feed is new.") }

                    if currentFeed.dataType == RealtimeEntityType.schedule { // add_gtfs_schedule_source

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

                    } else if RealtimeEntityType.allAsEnum.contains(currentFeed.dataType) {  // add_gtfs_realtime_source
                        
                        let entityTypeString : String = currentFeed.dataType.realtimeCode()

                        PYTHON_SCRIPT_ARGS_TEMP = """
                        add_gtfs_realtime_source(
                        entity_type=[\"\(entityTypeString)\"], 
                        provider=\"\(currentFeed.provider)\", 
                        direct_download_url=\"\(currentFeed.downloadURL)\", 
                        authentication_type=\(currentFeed.authenticationType), 
                        authentication_info_url=\"\(currentFeed.authenticationInfoURL)\", 
                        api_key_parameter_name=\"\(currentFeed.apiKeyParameterName)\", 
                        license_url=\"\(currentFeed.licenseURL)\", 
                        name=\"\(currentFeed.name)\", 
                        note=\"\(currentFeed.note)\", 
                        status=\"\(currentFeed.status)\", 
                        feed_contact_email=\"\(currentFeed.dataProducerEmail)\")
                        """

                    }

                } else if currentFeed.issueType == IssueType.isFeedUpdate {

                    if isInDebugMode { print("\t\tCurrent feed is update.") }

                    if currentFeed.dataType == RealtimeEntityType.schedule { // update_gtfs_schedule_source

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

                    } else if RealtimeEntityType.allAsEnum.contains(currentFeed.dataType) {  // update_gtfs_realtime_source
                        
                        let entityTypeString : String = currentFeed.dataType.realtimeCode()
                        
                        PYTHON_SCRIPT_ARGS_TEMP = """
                        update_gtfs_realtime_source(
                        mdb_source_id=\(currentFeed.oldMobilityDatabaseID), 
                        entity_type=[\"\(entityTypeString)\"], 
                        provider=\"\(currentFeed.provider)\", 
                        authentication_type=\(currentFeed.authenticationType), 
                        authentication_info_url=\"\(currentFeed.authenticationInfoURL)\", 
                        api_key_parameter_name=\"\(currentFeed.apiKeyParameterName)\", 
                        name=\"\(currentFeed.name)\", 
                        note=\"\(currentFeed.note)\", 
                        status=\"\(currentFeed.status)\", 
                        feed_contact_email=\"\(currentFeed.dataProducerEmail)\")
                        """

                    }

                } else if currentFeed.issueType == IssueType.isToRemoveFeed {

                    if isInDebugMode { print("\t\tCurrent feed is to be removed.") }

                    if currentFeed.dataType == RealtimeEntityType.schedule { // update_gtfs_schedule_source

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


                    } else if RealtimeEntityType.allAsEnum.contains(currentFeed.dataType) {  // update_gtfs_realtime_source
                        
                        let entityTypeString : String = currentFeed.dataType.realtimeCode()

                        PYTHON_SCRIPT_ARGS_TEMP = """
                        update_gtfs_realtime_source(
                        mdb_source_id=\(currentFeed.oldMobilityDatabaseID), 
                        entity_type=\"[\(entityTypeString)]\", 
                        provider=\"\(currentFeed.provider)\", 
                        authentication_type=\(currentFeed.authenticationType), 
                        authentication_info_url=\"\(currentFeed.authenticationInfoURL)\", 
                        api_key_parameter_name=\"\(currentFeed.apiKeyParameterName)\", 
                        name=\"\"**** issued for removal ****\"\", 
                        note=\"\(currentFeed.note)\", 
                        status=\"\(currentFeed.status)\", 
                        feed_contact_email=\"\(currentFeed.dataProducerEmail)\")
                        """

                    }

                } else if currentFeed.issueType == IssueType.isUnknown { // assume default is .isAddNewFeed

                    if isInDebugMode { print("\t\tCurrent feed is assumed to be new.") }

                    if currentFeed.dataType == RealtimeEntityType.schedule { // add_gtfs_schedule_source

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

                    } else if RealtimeEntityType.allAsEnum.contains(currentFeed.dataType) {  // add_gtfs_realtime_source
                        
                        let entityTypeString : String = currentFeed.dataType.realtimeCode()

                        PYTHON_SCRIPT_ARGS_TEMP = """
                        add_gtfs_realtime_source(
                        entity_type=\"[\(entityTypeString)]\", 
                        provider=\"\(currentFeed.provider)\", 
                        direct_download_url=\"\(currentFeed.downloadURL)\", 
                        authentication_type=\(currentFeed.authenticationType), 
                        authentication_info_url=\"\(currentFeed.authenticationInfoURL)\", 
                        api_key_parameter_name=\"\(currentFeed.apiKeyParameterName)\", 
                        license_url=\"\(currentFeed.licenseURL)\", 
                        name=\"\(currentFeed.name)\", 
                        note=\"\(currentFeed.note)\", 
                        status=\"\(currentFeed.status)\", 
                        feed_contact_email=\"\(currentFeed.dataProducerEmail)\")
                        """

                    }

                }

                // Let's remove the added newline characters
                PYTHON_SCRIPT_ARGS_TEMP = PYTHON_SCRIPT_ARGS_TEMP.replacingOccurrences(of: defaults.newline, with: "")
                
                if isInDebugMode { print("\t\tResulting Python command :\n\t\t\(PYTHON_SCRIPT_ARGS_TEMP)\n")}
                
                if !PYTHON_SCRIPT_ARGS_TEMP.isEmpty { PYTHON_SCRIPT_OUTPUT += (PYTHON_SCRIPT_OUTPUT.isEmpty ? "" : defaults.finalOutputDivider) + PYTHON_SCRIPT_ARGS_TEMP }
                
            } // END FOR LOOP

            // Replace single quotes (like in McGill's) with an apostrophe so there is no interference with the bash script in the next step.
            PYTHON_SCRIPT_OUTPUT = PYTHON_SCRIPT_OUTPUT.replacingOccurrences(of: defaults.singleQuote, with: defaults.apostrophe)
            // Note: do not try to fix the ouput of multiple quotes (ex.: """") as it will break the python script.
            
            // Remove empty parameters from script output
            PYTHON_SCRIPT_OUTPUT = removeEmptyPythonParameters(in: PYTHON_SCRIPT_OUTPUT)
            
            // Print the final output in a readable format for debugging or in plain format for the Python script to process.
            if isInDebugMode { print("\n\nFINAL OUTPUT:\n\n" + prettyPrintPythonCommands(input: PYTHON_SCRIPT_OUTPUT))} else { print(PYTHON_SCRIPT_OUTPUT) }

            exit(0)

        } else {
            throw ScriptError.incorrectArgumentsCount
        }
    } catch ScriptError.noData {
        print("ERROR: \(ScriptError.noData.description)") ; exit(1)
    } catch ScriptError.networkError {
        print("ERROR:\(ScriptError.networkError.description) ") ; exit(2)
    } catch ScriptError.parseError {
        print("ERROR: \(ScriptError.parseError.description)") ; exit(2)
    } catch ScriptError.incorrectArgumentsCount {
        print("ERROR: \(ScriptError.incorrectArgumentsCount.description)") ; exit(1)
    } catch ScriptError.insufficientNumberOfColumns {
        print("ERROR: \(ScriptError.insufficientNumberOfColumns.description)") ; exit(1)
    } catch {
        print("ERROR: Unexpected error: \(error.localizedDescription)") ;  exit(255)  // General error catch-all
    }
}

// MARK: - FUNCTIONS

/// Downloads and parses a CSV file from a given URL, converting dates according to specified formats.
///
/// This function performs several key operations:
/// - Validates the provided URL
/// - Downloads the CSV content
/// - Checks that the downloaded content is not empty
/// - Parses the CSV into an array of `feed` objects
///
/// - Parameters:
///   - fromURL: The complete URL string pointing to the CSV file to be downloaded
///   - dateFormatRegex: A regular expression pattern to match the current date format in the CSV
///   - dateFormatDesired: The target date format to convert dates to
///
/// - Returns: An array of `feed` objects parsed from the CSV
///
/// - Throws: 
///   - `ScriptError.networkError` if the URL is invalid
///   - `ScriptError.noData` if the downloaded CSV is empty
///   - Other potential errors from file reading or parsing processes
func downloadAndParseCSV(fromURL: String, dateFormatRegex: String, dateFormatDesired: String) throws -> [feed]  {

    guard let csvURLasURL : URL = URL(string: fromURL) else { throw ScriptError.networkError }

    do {

        let csvData : String = try String(contentsOf: csvURLasURL, encoding: .utf8)
        guard !csvData.isEmpty else { throw ScriptError.noData }
        
        let csvLines : [String] = csvData.components(separatedBy: defaults.csvLineSeparator)
        let csvArray : [feed]   = try parseCSV(csvLines: csvLines, columnSeparator: defaults.csvColumnSeparator, dateFormatRegex: dateFormatRegex, dateFormatDesired: dateFormatDesired)
        
        return csvArray

    } catch {
        throw error
    }
}

/// Parses an array of CSV lines into an array of `feed` instances.
/// - Parameters:
///   - csvLines: An array of strings, each representing a row from the CSV file.
///   - columnSeparator: A string used to separate columns within each row.
///   - dateFormatRegex: A regex pattern to match the date format in the CSV data.
///   - dateFormatDesired: A string representing the desired date format for output.
/// - Returns: An array of `feed` instances constructed from the CSV data.
func parseCSV(csvLines: [String], columnSeparator: String, dateFormatRegex: String, dateFormatDesired: String) throws -> [feed] {

    do {
        if isInDebugMode { print("\n\t\tProcessing CSV Array column...\n") }

        var feeds: [feed] = []
        var lastKnownProvider : String = defaults.toBeProvided
        let dateFormatAsRegex: Regex<AnyRegexOutput>? = try? Regex(dateFormatRegex)
        var counter : Int = 1
        
        for line: String in csvLines {

            // Separate the columns and verify there's enough columns to proceed
            let csvArrayColumn : [String] = line.components(separatedBy: columnSeparator)
            if isInDebugMode { print("\t\t\t- Column count for item \(counter) : \(csvArrayColumn.count)") }
            guard csvArrayColumn.count >= column.count else {
                print("Expected at least \(column.count) columns, but got \(csvArrayColumn.count) instead.")
                throw ScriptError.insufficientNumberOfColumns
            }

            // Get issue and data types
            let issueTypeValue : IssueType = issueType(for : csvArrayColumn[column.issueType].trimmingCharacters(in: .whitespacesAndNewlines))
            let dataTypeValue  : RealtimeEntityType  = dataType(for : csvArrayColumn[column.datatype].count < 3 ? RealtimeEntityType.empty.asString : csvArrayColumn[column.datatype])

            // Format timestamp properly
            let timestampFormatted : String = extractDate(from : csvArrayColumn[column.timestamp].trimmingCharacters(in: .whitespacesAndNewlines), 
                                                          usingGREP : dateFormatAsRegex!, 
                                                          desiredDateFormat : dateFormatDesired)

            // Check if provider is empty, suggest last known if true.
            var provider: String = csvArrayColumn[column.provider].trimmingCharacters(in: .whitespacesAndNewlines)
            if provider.count > 0 { lastKnownProvider = provider } ; provider = provider.isEmpty ? "\(defaults.toBeProvided) (\(lastKnownProvider) ?)" : provider

            // Check if download URL is valid
            var downloadURLvalue : String = csvArrayColumn[column.downloadurl].trimmingCharacters(in: .whitespacesAndNewlines)
            if (!isURLPresent(in: downloadURLvalue) && !downloadURLvalue.isEmpty) { downloadURLvalue = defaults.emptyValue }

            // Check if license URL is valid
            var licenseURLvalue : String = csvArrayColumn[column.license_url].trimmingCharacters(in: .whitespacesAndNewlines)
            if (!isURLPresent(in: licenseURLvalue) && !licenseURLvalue.isEmpty) { licenseURLvalue = defaults.emptyValue }

            // Get authentification Int
            let authTypeValue : Int = authenticationType(for: csvArrayColumn[column.authentication_type].trimmingCharacters(in: .whitespacesAndNewlines))

            let newFeed : feed = feed (
                fourZeroThreeClientError    : csvArrayColumn[column.fourZeroThreeClientError],
                timestamp                   : timestampFormatted,
                provider                    : provider,
                oldMobilityDatabaseID       : Int(csvArrayColumn[column.oldMobilityDatabaseID].trimmingCharacters(in: .escapedDoubleQuote)) ?? 0,
                dataType                    : dataTypeValue,
                dataTypeString              : csvArrayColumn[column.datatype].count < 3 ? RealtimeEntityType.empty.asString : csvArrayColumn[column.datatype],
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
                redirects                   : redirectArray(for: csvArrayColumn[column.redirects]),
                dataProducerEmail           : csvArrayColumn[column.dataproduceremail].trimmingCharacters(in: .whitespacesAndNewlines)
            )
            
            feeds.append(newFeed)
            counter += 1
        }
        
        return feeds

    }
}

/// Determines the `IssueType` based on the provided string value.
/// - Parameter issueTypeValue: A `String` representing the issue type, which may contain certain keywords.
/// - Returns: An `IssueType` enum value based on the provided string. If no match is found, returns `.unknown`.
func issueType(for issueTypeValue: String) -> IssueType {
    let issueTypeMappings: [(IssueType, [String])] = [
        (.isAddNewFeed, [IssueType.isAddNewFeed.asString.lowercased(), IssueType.isAddNewSource.asString.lowercased()]),
        (.isFeedUpdate, [IssueType.isUpdateExistingFeed.asString.lowercased(), IssueType.isFeedUpdate.asString.lowercased()]),
        (.isToRemoveFeed, [IssueType.isToRemoveFeed.asString.lowercased()])
    ]
    
    return issueTypeMappings.first { (_: IssueType, keywords : [String] ) in
        keywords.contains { issueTypeValue.lowercased().contains($0) }
    }?.0 ?? .isUnknown
}

/// Determines the `DataType` based on the provided string value.
/// - Parameter dataTypeValue: A `String` representing the data type, which may contain certain keywords.
/// - Returns: A `DataType` enum value based on the provided string. If no match is found, returns `.unknown`.
func dataType(for value: String) -> RealtimeEntityType {

    var result : RealtimeEntityType = .unknown // Default to `.unknown` if no match is found

    func normalize(_ string: String) -> String {
        return string.replacingOccurrences(of: "\\s+", with: "", options: .regularExpression).lowercased()
    }

    if let index: Array<String>.Index = RealtimeEntityType.allAsStrings.firstIndex(where: { normalize(value).contains(normalize($0)) }) {
        // Use the index to return the corresponding enum case from allCases
        result = RealtimeEntityType.allCases[index]
    }

    if isInDebugMode { print("\t\t\t\t- Input value: \(value), Result: \(result.asString)") }
    
    return result
}


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
func extractDate(from dateToConvert: String, usingGREP dateFormatAsGREP: Regex<AnyRegexOutput>, desiredDateFormat: String) -> String {
    // Attempt to find the first match in the input string
    guard let match       : Regex<Regex<AnyRegexOutput>.RegexOutput>.Match = dateToConvert.firstMatch(of: dateFormatAsGREP),
          let matchOutput : Substring = match.output[0].substring else { return defaults.date } // Return default if no match

    // Configure the date formatter
    let dateFormatter : DateFormatter = DateFormatter() ; dateFormatter.dateFormat = desiredDateFormat

    // Attempt to parse and format the date, or return default if parsing fails
    if let date : Date = dateFormatter.date(from: String(matchOutput)) { return dateFormatter.string(from: date) }
    return defaults.date
}

/// Generates a Python-like array inside a string from a comma-separated input string.
///
/// This function takes a raw input string, splits it by commas, and formats each element into a specific JSON-like structure with `id` and `comment` keys. If the input string is empty, it returns a default empty value.
///
/// - Parameter rawData: A comma-separated string of values to be formatted.
/// - Returns: A Python-like array inside a string representating the input values, or a default empty value if the input is empty.
///
/// - Note: The default empty value is provided by `defaults.emptyValue`.
func redirectArray(for rawData: String) -> String {
    guard !rawData.isEmpty else { return defaults.emptyValueRaw }

    let openingPrefix       : String = ", redirects=["
    let prefix              : String = "{\"\"id\"\": "
    let suffix              : String = ", \"\"comment\"\": \"\" \"\"}"
    let closingSuffix       : String = "]"
    let keyValuePairsJoiner : String = ", "

    let rawDataClean : String = rawData.replacingOccurrences(of: "\"", with: "")

    guard rawDataClean.count >= 3 else { return "\(openingPrefix)\(closingSuffix)" }

    let redirectEntries : String = rawDataClean
        .components(separatedBy: defaults.whitespace)
        .map { prefix + $0 + suffix }
        .joined(separator: keyValuePairsJoiner)

    return "\(openingPrefix)\(redirectEntries)\(closingSuffix)"
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
    let range: Range<String.Index>? = string.range(of: defaults.httpAddressPattern, options: .regularExpression)
    if range != nil { return true }
    return false
}

/// Removes empty parameter definitions from a Python script output string.
///
/// - Parameter outputString: The string containing the Python script output.
/// - Returns: A new string with empty parameter definitions removed. The original string remains unmodified.
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
    return defaults.everyPythonScriptFunctionsParameterNames.reduce(outputString) { result, parameter in
        let firstPass  : String = ", \(parameter)\(defaults.doubleQuotes)"
        let secondPass : String = "\(parameter)\(defaults.doubleQuotes), "
        
        return result
            .replacingOccurrences(of: firstPass, with: "")
            .replacingOccurrences(of: secondPass, with: "")
    }
}

/// Formats a block of Python commands into a more readable format for debugging.
/// 
/// This function takes a string of Python commands separated by the `defaults.finalOutputDivider` character, formats each command by breaking its arguments onto new lines with tabs, and returns the resulting formatted string. Commands that don't match the expected pattern (e.g., missing parentheses) are returned unmodified.
///
/// - Parameter input: A string containing Python commands separated by the `defaults.finalOutputDivider` character.
/// - Returns: A formatted string where each command is separated by two newlines, with arguments neatly displayed on individual lines.
func prettyPrintPythonCommands(input: String) -> String {
    
    // Split the input into individual Python commands using the `defaults.finalOutputDivider` separator
    let commands: [String] = input.components(separatedBy: defaults.finalOutputDivider)
    
    // Process each command
    let formattedCommands: [String] = commands.map { command -> String in

        // Find the arguments part of the command (inside parentheses)
        guard let argsStartIndex: String.Index = command.firstIndex(of: "("),
              let argsEndIndex: String.Index = command.lastIndex(of: ")") else { return command }
        
        // Extract the function name and arguments
        let functionName: String.SubSequence = command[..<argsStartIndex]
        let arguments: Substring = command[command.index(after: argsStartIndex)..<argsEndIndex]
        
        // Format arguments by splitting them with ',' and adding newlines + tabs
        let formattedArguments: String = arguments
            .components(separatedBy: defaults.comma)
            .map { "\t\($0.trimmingCharacters(in: .whitespacesAndNewlines))" }
            .joined(separator: defaults.comma + defaults.newline)
        
        // Rebuild the command with the formatted arguments
        let formattedCommand : String = "\(functionName)(\n\(formattedArguments)\n)"
        
        // Fix the specific issue with comment formatting
        return formattedCommand //.replacingOccurrences(of: ",\n\t\"\"comment\": \"\"}]", with: ", \"\"comment\": \"\"}]")
    }
    
    // Join all the formatted commands with two newlines
    return formattedCommands.joined(separator: defaults.newline + defaults.newline)
}

// MARK: - EXTENSIONS

extension CharacterSet {
    static let escapedDoubleQuote : CharacterSet = CharacterSet(charactersIn: "\"")
}

extension feed {

    /// Provides a textual description of the `feed` instance.
    /// 
    /// The `description` property generates a detailed, human-readable summary of the feed's attributes, including provider, data type, issue type, download URL, location details, and additional metadata. This description is formatted for easy readability and is useful for debugging or logging feed details.
    var description: String {
        """
        \t\tFEED DETAILS:
        \t\t  - Timestamp :                 \(timestamp)
        \t\t  - Provider :                  \(provider)
        \t\t  - Old Mobility Database ID :  \(oldMobilityDatabaseID)
        \t\t  - Data Type :                 \(dataType)
        \t\t  - Issue Type :                \(issueType)
        \t\t  - Download URL :              \(downloadURL)
        \t\t  - Country :                   \(country)
        \t\t  - Subdivision :               \(subdivisionName)
        \t\t  - Municipality :              \(municipality)
        \t\t  - Name :                      \(name)
        \t\t  - License URL :               \(licenseURL)
        \t\t  - Authentification type :     \(authenticationType)
        \t\t  - Authentification Info URL : \(authenticationInfoURL)
        \t\t  - Header or API key :         \(apiKeyParameterName)
        \t\t  - Notes :                     \(note)
        \t\t  - Status :                    \(status)
        \t\t  = Redirects :                 \(redirects)
        \t\t  = Data Producer Email :       \(dataProducerEmail)
        """
    }

}
