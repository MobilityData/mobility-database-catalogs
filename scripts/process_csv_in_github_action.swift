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
}

struct defaults {
    static let date                      : String = "01/01/1970"
    static let toBeProvided              : String = "TO_BE_PROVIDED"
    static let emptyValue                : String = "\"\""
    static let emptyValueRaw             : String = ""
    static let csvLineSeparator          : String = "\n"
    static let csvColumnSeparator        : String = ","
}

struct issueType {
    static let isAddNewFeed              : String = "New feed"
    static let isAddNewSource            : String = "New source"
    static let isUpdateExistingFeed      : String = "Source update"
    static let isFeedUpdate              : String = "Feed update"
    static let isToRemoveFeed            : String = "removed"
}

struct dataType {
    static let schedule                  : String = "Schedule"
    static let realtime                  : String = "Realtime"
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

// Will be used to filter empty parameters from this script's output
let everyPythonScriptFunctionsParameterNames : [String] = ["provider=", "entity_type=", "country_code=", "authentication_type=", "authentication_info_url=", "api_key_parameter_name=", "subdivision_name=", "municipality=", "country_code=", "license_url=", "name=", "status=", "features=", "note=", "feed_contact_email=", "redirects="]

let argNames : [String] = CommandLine.arguments
// let argNames : [String] = ["scriptname", "https://docs.google.com/spreadsheets/d/1Q96KDppKsn2khdrkraZCQ7T_qRSfwj7WsvqXvuMt4Bc/gviz/tq?tqx=out:csv;outFileName:data&sheet=%5BCLEANED%5D%20For%20import", "11/11/2024", "[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2}", "MM/dd/yyyy"]

// Set to false for production use
let isInDebugMode : Bool = false

if argNames.count == 5 {
    
    let csvURLStringArg      : String = argNames[1] // the first argName  [0] is the name of the script, we can ignore in this context.
    let dateToFind           : String = argNames[2]
    let dateFormatGREPArg    : String = argNames[3]
    let dateFormatDesiredArg : String = argNames[4]
    
    guard let csvURLasURL : URL = URL(string: csvURLStringArg) else {
        print("\n   ERROR: The specified URL does not appear to exist :\n   \(csvURLStringArg)\n")
        exit(1)
    }
    
    let dateFormatter : DateFormatter = DateFormatter() //; let today : Date = Date()
    dateFormatter.dateFormat = dateFormatDesiredArg
    
    let csvData : String = try String(contentsOf: csvURLasURL, encoding:.utf8)
    
    var csvLines : [String] = csvData.components(separatedBy: defaults.csvLineSeparator) ; csvLines.removeFirst(1) ; var csvArray : [[String]] = []
    for currentLine : String in csvLines {
        if currentLine.count > 5 { csvArray.append(currentLine.components(separatedBy: defaults.csvColumnSeparator)) }
    }
    csvArray.removeFirst() // We don't need the header row
    
    if isInDebugMode { print("\n\n\t\tcsvArray (\(csvArray.count) item(s)) : \(csvArray)") }
    
    var PYTHON_SCRIPT_OUTPUT : String = ""
    var lastKnownProvider : String = defaults.toBeProvided
    let dateFormatAsRegex : Regex<AnyRegexOutput> = try Regex(dateFormatGREPArg)
    
    for csvArrayColumn : [String] in csvArray {
        
        var PYTHON_SCRIPT_ARGS_TEMP : String = ""
        if isInDebugMode { print("column count / all cases count : \(csvArrayColumn.count) / \(column.allCases.count)") }
        
        if csvArrayColumn.count >= column.allCases.count {
            
            if isInDebugMode { print("\nprocessing CSV Array column...") }
            
            let timestamp               : String = csvArrayColumn[column.timestamp].trimmingCharacters(in: .whitespacesAndNewlines)
            let provider                : String = csvArrayColumn[column.provider]
            let old_mbd_ID_String       : String = csvArrayColumn[column.oldMobilityDatabaseID].trimmingCharacters(in: CharacterSet(charactersIn: "\"")) // We need to remove the trailing quotation 
            let datatype                : String = csvArrayColumn[column.datatype].count < 3 ? realtimeEntityTypes.empty : csvArrayColumn[column.datatype]
            let issue                   : String = csvArrayColumn[column.issueType]
            let downloadURL             : String = csvArrayColumn[column.downloadurl]
            let country                 : String = csvArrayColumn[column.country]
            let subdivision_name        : String = csvArrayColumn[column.subdivision_name]
            let municipality            : String = csvArrayColumn[column.municipality]
            let name                    : String = csvArrayColumn[column.name]
            var license_url             : String = csvArrayColumn[column.license_url]
            let authentication_type     : String = csvArrayColumn[column.authentication_type]
            let authentication_info_url : String = csvArrayColumn[column.authentication_info_url]
            let api_key_parameter_name  : String = csvArrayColumn[column.api_key_parameter_name]
            let note                    : String = csvArrayColumn[column.note]
            let status                  : String = csvArrayColumn[column.status]
            let redirects               : String = csvArrayColumn[column.redirects].trimmingCharacters(in: .whitespacesAndNewlines).trimmingCharacters(in: CharacterSet(charactersIn: "\""))
            let dataproduceremail       : String = csvArrayColumn[column.dataproduceremail]
            let old_mbd_ID              : Int    = Int(old_mbd_ID_String) ?? 0

            if isInDebugMode { print("\t\tdatatype : \(datatype)") }
            if isInDebugMode { print("\t\tissue    : \(issue)") }
            
            // Check if provider is empty, suggest last known if true.
            if provider.count > 0 { lastKnownProvider = provider }
            let finalProvider : String = provider.isEmpty ? "\(defaults.toBeProvided) (\(lastKnownProvider) ?)" : provider
            
            // Create redirects array
            let redirects_array : String = redirectArray(for: redirects)
            if isInDebugMode { print("\t\tredirects_array : \(redirects_array)") }
            
            // Check if license URL is valid
            let urlPresent : Bool = isURLPresent(in: license_url)
            if ( urlPresent == false && license_url.count > 0 ) { license_url = defaults.emptyValue }
            
            let dateFromCurrentLine : String = extractDate(from: timestamp, usingGREP: dateFormatAsRegex, desiredDateFormat: dateFormatDesiredArg)
            
            if isInDebugMode { print("\t\ttimestamp // dateFromCurrentLine // dateToFind : \(timestamp) // \(dateFromCurrentLine) // \(dateToFind)") }
            // if isInDebugMode { print("\t\tupdatednewsourceurl || downloadURL : \(updatednewsourceurl) (\(updatednewsourceurl.count)) \(downloadURL) (\(downloadURL.count))") }
            
            var scheduleFinalURLtoUse : String = downloadURL ; if downloadURL.count < 4 { scheduleFinalURLtoUse = defaults.emptyValue }
            var realtimeFinalURLtoUse : String = downloadURL ; if downloadURL.count < 4 { realtimeFinalURLtoUse = defaults.emptyValue }
            
            if isInDebugMode { print("\t\tscheduleFinalURLtoUse || realtimeFinalURLtoUse : \(scheduleFinalURLtoUse) (\(scheduleFinalURLtoUse.count)) \(realtimeFinalURLtoUse) (\(realtimeFinalURLtoUse.count))") }
            if isInDebugMode { print("\t\tEvaluating issue: \(issue)") }

            if issue.contains(issueType.isAddNewFeed) || issue.contains(issueType.isAddNewSource) { // add new feed

                if isInDebugMode { print("\t\t\tNEW FEED: issue contains datatype: \(datatype)") }
                
                if datatype.contains(dataType.schedule) { // add_gtfs_schedule_source
                
                    let authType : Int = authenticationType(for: authentication_type)
                    
                    PYTHON_SCRIPT_ARGS_TEMP  = """
                    add_gtfs_schedule_source(
                    provider=\"\(finalProvider)\", 
                    country_code=\"\(country)\", 
                    direct_download_url=\"\(scheduleFinalURLtoUse)\", 
                    authentication_type=\(authType), 
                    authentication_info_url=\"\(authentication_info_url)\", 
                    api_key_parameter_name=\"\(api_key_parameter_name)\", 
                    subdivision_name=\"\(subdivision_name)\", 
                    municipality=\"\(municipality)\", 
                    license_url=\"\(license_url)\", 
                    name=\"\(name)\", 
                    status=\"\(status)\", 
                    feed_contact_email=\"\(dataproduceremail)\"
                    \(redirects_array))
                    """
                    
                } else if datatype.contains(dataType.realtime) || (datatype.contains(realtimeEntityTypesString.vehiclePositions)) || (datatype.contains(realtimeEntityTypesString.tripUpdates)) || (datatype.contains(realtimeEntityTypesString.serviceAlerts)) || (datatype.contains(realtimeEntityTypesString.unknown)) { // add_gtfs_realtime_source
                    // Emma: entity_type matches the realtime Data type options of Vehicle Positions, Trip Updates, or Service Alerts. If one of those three are selected, add it. If not, omit it.
                    
                    let authType : Int = authenticationType(for: authentication_type)
                    let realtimecode : Array = realtimeCode(for: datatype)
                    let realtimecodeString: String = realtimecode.joined(separator:"\", \"")
                    
                    PYTHON_SCRIPT_ARGS_TEMP = """
                    add_gtfs_realtime_source(
                    entity_type=[\"\(realtimecodeString)\"], 
                    provider=\"\(finalProvider)\", 
                    direct_download_url=\"\(realtimeFinalURLtoUse)\", 
                    authentication_type=\(authType), 
                    authentication_info_url=\"\(authentication_info_url)\", 
                    api_key_parameter_name=\"\(api_key_parameter_name)\", 
                    license_url=\"\(license_url)\", 
                    name=\"\(name)\", 
                    note=\"\(note)\", 
                    status=\"\(status)\", 
                    feed_contact_email=\"\(dataproduceremail)\"
                    \(redirects_array))
                    """
                    
                }
                
            } else if issue.contains(issueType.isUpdateExistingFeed) || issue.contains(issueType.isFeedUpdate) { // update existing feed

                if isInDebugMode { print("\t\t\tIS UPDATE: issue contains datatype: \(datatype)") }
                
                if datatype.contains(dataType.schedule) { // update_gtfs_schedule_source
                    
                    let authType : Int = authenticationType(for: authentication_type)
                    
                    PYTHON_SCRIPT_ARGS_TEMP = """
                    update_gtfs_schedule_source(mdb_source_id=\(old_mbd_ID), 
                    provider=\"\(finalProvider)\", 
                    name=\"\(name)\", 
                    country_code=\"\(country)\", 
                    subdivision_name=\"\(subdivision_name)\", 
                    municipality=\"\(municipality)\", 
                    authentication_type=\(authType), 
                    authentication_info_url=\"\(authentication_info_url)\", 
                    api_key_parameter_name=\"\(api_key_parameter_name)\", 
                    status=\"\(status)\", 
                    feed_contact_email=\"\(dataproduceremail)\"
                    \(redirects_array))
                    """
                    
                } else if datatype.contains(dataType.realtime) || datatype.contains(realtimeEntityTypesString.vehiclePositions) || datatype.contains(realtimeEntityTypesString.tripUpdates) || datatype.contains(realtimeEntityTypesString.serviceAlerts) || datatype.contains(realtimeEntityTypesString.unknown) || datatype.contains(realtimeEntityTypes.empty) { // update_gtfs_realtime_source
                    
                    let authType : Int = authenticationType(for: authentication_type)
                    let realtimecode : Array = realtimeCode(for: datatype)
                    let realtimecodeString: String = realtimecode.joined(separator:"\", \"")
                    
                    PYTHON_SCRIPT_ARGS_TEMP = """
                    update_gtfs_realtime_source(
                    mdb_source_id=\(old_mbd_ID), 
                    entity_type=[\"\(realtimecodeString)\"], 
                    provider=\"\(finalProvider)\", 
                    authentication_type=\(authType), 
                    authentication_info_url=\"\(authentication_info_url)\", 
                    api_key_parameter_name=\"\(api_key_parameter_name)\", 
                    name=\"\(name)\", 
                    note=\"\(note)\", 
                    status=\"\(status)\", 
                    feed_contact_email=\"\(dataproduceremail)\"
                    \(redirects_array))
                    """
                }
                
            }  else if issue.contains(issueType.isToRemoveFeed) { // remove feed

                if isInDebugMode { print("\t\t\tREMOVE FEED: issue contains datatype: \(datatype)") }
                
                if datatype.contains(dataType.schedule) { // update_gtfs_schedule_source
                    
                    let authType : Int = authenticationType(for: authentication_type)
                    
                    PYTHON_SCRIPT_ARGS_TEMP = """
                    update_gtfs_schedule_source(
                    mdb_source_id=\(old_mbd_ID), 
                    provider=\"\(finalProvider)\", 
                    name=\"\"**** issued for removal ****\"\", 
                    country_code=\"\(country)\", 
                    subdivision_name=\"\(subdivision_name)\", 
                    municipality=\"\(municipality)\", 
                    authentication_type=\(authType), 
                    authentication_info_url=\"\(authentication_info_url)\", 
                    api_key_parameter_name=\"\(api_key_parameter_name)\", 
                    status=\"\(status)\", 
                    feed_contact_email=\"\(dataproduceremail)\"
                    \(redirects_array))
                    """
                    
                } else if datatype.contains(dataType.realtime) || datatype.contains(realtimeEntityTypesString.vehiclePositions) || datatype.contains(realtimeEntityTypesString.tripUpdates) || datatype.contains(realtimeEntityTypesString.serviceAlerts) || datatype.contains(realtimeEntityTypesString.unknown) || datatype.contains(realtimeEntityTypes.empty) { // update_gtfs_realtime_source
                    
                    let authType : Int = authenticationType(for: authentication_type)
                    let realtimecode : Array = realtimeCode(for: datatype)
                    let realtimecodeString: String = realtimecode.joined(separator:"\", \"")
                    
                    PYTHON_SCRIPT_ARGS_TEMP = """
                    update_gtfs_realtime_source(
                    mdb_source_id=\(old_mbd_ID), 
                    entity_type=\"[\(realtimecodeString)]\", 
                    provider=\"\(finalProvider)\", 
                    authentication_type=\(authType), 
                    authentication_info_url=\"\(authentication_info_url)\", 
                    api_key_parameter_name=\"\(api_key_parameter_name)\", 
                    name=\"\"**** issued for removal ****\"\", 
                    note=\"\(note)\", 
                    status=\"\(status)\", 
                    feed_contact_email=\"\(dataproduceremail)\"
                    \(redirects_array))
                    """
                    
                }
                
            } else { // ... assume this is a new feed by default :: add_gtfs_schedule_source
                if isInDebugMode { print("\t\t\tDEFAULT: issue contains datatype: \(datatype)") }
                
                if datatype.contains(dataType.schedule) { // add_gtfs_schedule_source
                    
                    let authType : Int = authenticationType(for: authentication_type)

                    PYTHON_SCRIPT_ARGS_TEMP = """
                    add_gtfs_schedule_source(
                    provider=\"\(finalProvider)\", 
                    country_code=\"\(country)\", 
                    direct_download_url=\"\(scheduleFinalURLtoUse)\", 
                    authentication_type=\(authType), 
                    authentication_info_url=\"\(authentication_info_url)\", 
                    api_key_parameter_name=\"\(api_key_parameter_name)\", 
                    subdivision_name=\"\(subdivision_name)\", 
                    municipality=\"\(municipality)\", 
                    license_url=\"\(license_url)\", 
                    name=\"\(name)\", 
                    status=\"\(status)\", 
                    feed_contact_email=\"\(dataproduceremail)\"
                    \(redirects_array))
                    """
                    
                } else if datatype.contains(dataType.realtime) || (datatype.contains(realtimeEntityTypesString.vehiclePositions)) || (datatype.contains(realtimeEntityTypesString.tripUpdates)) || (datatype.contains(realtimeEntityTypesString.serviceAlerts)) || (datatype.contains(realtimeEntityTypesString.unknown)) { // add_gtfs_schedule_source
                    
                    let authType : Int = authenticationType(for: authentication_type)
                    let realtimecode : Array = realtimeCode(for: datatype)
                    let realtimecodeString: String = realtimecode.joined(separator:"\", \"")
                    
                    PYTHON_SCRIPT_ARGS_TEMP = """
                    add_gtfs_realtime_source(
                    entity_type=[\"\(realtimecodeString)\"], 
                    provider=\"\(finalProvider)\", 
                    direct_download_url=\"\(realtimeFinalURLtoUse)\", 
                    authentication_type=\(authType), 
                    authentication_info_url=\"\(authentication_info_url)\", 
                    api_key_parameter_name=\"\(api_key_parameter_name)\", 
                    license_url=\"\(license_url)\", 
                    name=\"\(name)\", 
                    note=\"\(note)\", 
                    status=\"\(status)\", 
                    feed_contact_email=\"\(dataproduceremail)\"
                    \(redirects_array))
                    """
                    
                }
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
    print("Incorrect number of argName s provided to the script. Expected 4: a string with the URL, a date format and the date format desired.")
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

func authenticationType(for authString: String) -> Int {
    if authString.contains("0") { return 0 }
    if authString.contains("1") { return 1 }
    if authString.contains("2") { return 2 }
    return 0
}

/// Generates a list of real-time data codes based on the provided data type string.
///
/// - Parameter theDataType: A string representing the desired real-time data type.
/// - Returns:
///   An array of strings containing the corresponding real-time data codes. If no match is found, it returns a default array containing the trip updates code.
///
/// This function checks the provided data type string against predefined strings representing real-time data entities.
///   - If a match is found (e.g., "vehiclePositions"), the corresponding real-time data code (e.g., "realtimeEntityTypes.vehiclePositions") is added to the return array.
///   - The function supports checking for multiple data types using string containment checks.
///   - If no match is found for any of the predefined data types, the function adds the default "tripUpdates" code to the return array.
///
/// This function assumes that `realtimeEntityTypesString` and `realtimeEntityTypes` are constants containing predefined strings for real-time data entities and their corresponding codes.
func realtimeCode(for theDataType: String) -> [String] {
    var returnArray : [String] = []
    if theDataType.contains(realtimeEntityTypesString.vehiclePositions) { returnArray.append(realtimeEntityTypes.vehiclePositions)  }
    if theDataType.contains(realtimeEntityTypesString.tripUpdates) { returnArray.append(realtimeEntityTypes.tripUpdates) }
    if theDataType.contains(realtimeEntityTypesString.serviceAlerts) { returnArray.append(realtimeEntityTypes.serviceAlerts) }
    if returnArray.count < 1 { returnArray.append(realtimeEntityTypes.tripUpdates) }
    return returnArray
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
