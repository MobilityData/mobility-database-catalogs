import Foundation
#if canImport(FoundationNetworking)
    import FoundationNetworking
#endif

enum oldColumn : Int, CaseIterable {
    case timestamp               = 0 // A
    case provider                = 1 // B
    case regioncity              = 2 // C
    case currenturl              = 3 // D
    case updatednewsourceurl     = 4 // E
    case datatype                = 5 // F
    case issue                   = 6 // G
    case downloadurl             = 7 // H
    case country                 = 8 // I
    case subdivision_name        = 9 // J
    case municipality            = 10 // K
    case name                    = 11 // L
    case yournameorg             = 12 // M
    case license_url             = 13 // N
    case tripupdatesurl          = 14 // O
    case servicealertsurl        = 15 // P
    case genunknownrturl         = 16 // Q
    case authentication_type     = 17 // R
    case authentication_info_url = 18 // S
    case api_key_parameter_name  = 19 // T
    case note                    = 20 // U
    case gtfsschedulefeatures    = 21 // W
    case gtfsschedulestatus      = 22 // Y
    case gtfsrealtimestatus      = 23 // Z
    case youremail               = 24 // AA
    case dataproduceremail       = 25 // AB
    case realtimefeatures        = 26 // AC
    case isocountrycode          = 27 // AB
    case feedupdatestatus        = 28 // AC
}

enum column : Int, CaseIterable {
    case submissionType          = 0 // A
    case timestamp               = 1 // B
    case provider                = 2 // C
    case regioncity              = 3 // D — NOT IN USE
    case oldMobilityDatabaseID   = 4 // E
    case updatednewsourceurl     = 5 // F
    case datatype                = 6 // G
    case issue                   = 7 // H
    case downloadurl             = 8 // I
    case country                 = 9 // J
    case subdivision_name        = 10 // K
    case municipality            = 11 // L
    case name                    = 12 // M
    case yournameorg             = 13 // N
    case license_url             = 14 // O
    case tripupdatesurl          = 15 // P
    case servicealertsurl        = 16 // Q
    case genunknownrturl         = 17 // R
    case authentication_type     = 18 // S
    case authentication_info_url = 19 // T
    case api_key_parameter_name  = 20 // U
    case note                    = 21 // V
    case emptyColumn1            = 22 // W
    case gtfsschedulefeatures    = 23 // X
    case emptyColumn2            = 24 // Y
    case gtfsschedulestatus      = 25 // Z
    case gtfsrealtimestatus      = 26 // AA
    case gtfsredirect            = 36 // AK - NEW
    case dataproduceremail       = 27 // AB
    case officialProducer        = 28 // AC
    case dataproduceremail2      = 29 // AD - NEW
    case datatype2               = 30 // AE
    case youremail               = 31 // AF
    case realtimefeatures        = 32 // AG
    case emptyColumn3            = 33 // AH — NOT IN USE
    case isocountrycode          = 34 // AI
    case feedupdatestatus        = 35 // AJ
}

enum defaults: String {
    case date = "01/01/1970"
    case toBeProvided = "TO_BE_PROVIDED"
}

enum issueType: String {
    case isAddNewFeed = "New feed"
    case isAddNewSource = "New source"
    case isUpdateExistingFeed = "Source update"
    case isToRemoveFeed = "removed"
}

enum dataType: String {
    case schedule = "Schedule"
    case realtime = "Realtime"
}

enum realtimeEntityTypesString: String {
    case vehiclePositions = "Vehicle Positions"
    case tripUpdates = "Trip Updates"
    case serviceAlerts = "Service Alerts"
    case unknown = "general / unknown"
}

enum realtimeEntityTypes: String {
    case vehiclePositions = "vp"
    case tripUpdates = "tu"
    case serviceAlerts = "sa"
    case unknown = "gu"
}

// Will be used to filter empty parameters from this script's output
let everyPythonScriptFunctionsParameterNames : [String] = ["provider=", "entity_type=", "country_code=", "authentication_type=", "authentication_info_url=", "api_key_parameter_name=", "subdivision_name=", "municipality=", "country_code=", "license_url=", "name=", "status=", "features=", "note=", "feed_contact_email=", "redirects="]

let arguments : [String] = CommandLine.arguments
// let arguments : [String] = ["scriptname", "https://docs.google.com/spreadsheets/d/1Q96KDppKsn2khdrkraZCQ7T_qRSfwj7WsvqXvuMt4Bc/gviz/tq?tqx=out:csv;outFileName:data&sheet=%5BCLEANED%5D%20For%20import", "07/09/2024", "[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2}", "MM/dd/yyyy"]

// Set to false for production use
let isInDebugMode : Bool = false

if CommandLine.argc == 5 {

    let csvLineSeparator     : String = "\n"
    let csvColumnSeparator   : String = ","

    let csvURLStringArg      : String = arguments[1] // the first argument [0] is the name of the script, we can ignore in this context.
    let dateToFind           : String = arguments[2]
    let dateFormatGREPArg    : String = arguments[3]
    let dateFormatDesiredArg : String = arguments[4]

    guard let csvURLasURL : URL = URL(string: csvURLStringArg) else {
        print("\n   ERROR: The specified URL does not appear to exist :\n   \(csvURLStringArg)\n")
        exit(1)
    }
    
    let dateFormatter : DateFormatter = DateFormatter() //; let today : Date = Date()
    dateFormatter.dateFormat = dateFormatDesiredArg

    let csvData : String = try String(contentsOf: csvURLasURL, encoding:.utf8)

    var csvLines : [String] = csvData.components(separatedBy: csvLineSeparator) ; csvLines.removeFirst(1) ; var csvArray : [[String]] = []
    for currentLine : String in csvLines {
        if currentLine.count > 5 { csvArray.append(currentLine.components(separatedBy: csvColumnSeparator)) }
    }

    if isInDebugMode { print("\n\n\t\tcsvArray (\(csvArray.count) item(s)) : \(csvArray)") }
    
    var PYTHON_SCRIPT_OUTPUT : String = ""
    var lastKnownProvider : String = defaults.toBeProvided.rawValue
    let dateFormatAsRegex : Regex<AnyRegexOutput> = try Regex(dateFormatGREPArg)

    for csvArrayColumn : [String] in csvArray {
        
        var PYTHON_SCRIPT_ARGS_TEMP : String = ""
        if isInDebugMode { print("column count / all cases count : \(csvArrayColumn.count) / \(column.allCases.count)") }

        if csvArrayColumn.count >= column.allCases.count {

            if isInDebugMode { print("\nprocessing CSV Array column...") }

            let timestamp               : String = csvArrayColumn[column.timestamp.rawValue].trimmingCharacters(in: .whitespacesAndNewlines)
            let provider                : String = csvArrayColumn[column.provider.rawValue]
            let datatype                : String = csvArrayColumn[column.datatype.rawValue]
            let issue                   : String = csvArrayColumn[column.issue.rawValue]
            let country                 : String = csvArrayColumn[column.country.rawValue]
            let subdivision_name        : String = csvArrayColumn[column.subdivision_name.rawValue]
            let municipality            : String = csvArrayColumn[column.municipality.rawValue]
            let name                    : String = csvArrayColumn[column.name.rawValue]
            var license_url             : String = csvArrayColumn[column.license_url.rawValue]
            let downloadURL             : String = csvArrayColumn[column.downloadurl.rawValue]
            let updatednewsourceurl     : String = csvArrayColumn[column.updatednewsourceurl.rawValue]
            let authentication_type     : String = csvArrayColumn[column.authentication_type.rawValue]
            let authentication_info_url : String = csvArrayColumn[column.authentication_info_url.rawValue]
            let api_key_parameter_name  : String = csvArrayColumn[column.api_key_parameter_name.rawValue]
            let note                    : String = csvArrayColumn[column.note.rawValue]
            let gtfsschedulefeatures    : String = csvArrayColumn[column.gtfsschedulefeatures.rawValue]
            let gtfsschedulestatus      : String = csvArrayColumn[column.gtfsschedulestatus.rawValue].lowercased()
            let gtfsrealtimestatus      : String = csvArrayColumn[column.gtfsrealtimestatus.rawValue].lowercased()
            let realtimefeatures        : String = csvArrayColumn[column.realtimefeatures.rawValue]
            let redirects               : String = csvArrayColumn[column.gtfsredirect.rawValue]
            let feed_contact_email      : String = csvArrayColumn[column.dataproduceremail2.rawValue]
            let old_mbd_ID_String       : String = csvArrayColumn[column.oldMobilityDatabaseID.rawValue].trimmingCharacters(in: CharacterSet(charactersIn: "\"")) // We need to remove the trailing quotation marks from the value, they interfere with the conversion to Int.
            let old_mbd_ID              : Int    = Int(old_mbd_ID_String) ?? 0

            if isInDebugMode { print("\t\tdatatype : \(datatype)") }
            if isInDebugMode { print("\t\tissue    : \(issue)") }
            
            // Check if provider is empty, suggest last known if true.
            if provider.count > 0 { lastKnownProvider = provider }
            let finalProvider : String = provider.isEmpty ? "\(defaults.toBeProvided.rawValue) (\(lastKnownProvider) ?)" : provider

            // Create redirects array
            var redirects_array : String = "\"\"" // default value, the entire argument will be removed from the output.
            if redirects.count > 4 { redirects_array = "{\'id\': \(redirects), \'comment\': \'\'}" }
            if isInDebugMode { print("\t\tredirects_array : \(redirects_array)") }

            // Check if license URL is valid
            let urlPresent : Bool = isURLPresent(in: license_url)
            if ( urlPresent == false && license_url.count > 0 ) { license_url = "\"\"" }

            let dateFromCurrentLine : String = extractDate(from: timestamp, usingGREP: dateFormatAsRegex, desiredDateFormat: dateFormatDesiredArg)

            if isInDebugMode { print("\t\ttimestamp // dateFromCurrentLine // dateToFind : \(timestamp) // \(dateFromCurrentLine) // \(dateToFind)") }

            if isInDebugMode { print("\t\tupdatednewsourceurl || downloadURL : \(updatednewsourceurl) (\(updatednewsourceurl.count)) \(downloadURL) (\(downloadURL.count))") }

            var scheduleFinalURLtoUse : String = downloadURL ; if downloadURL.count < 4 { scheduleFinalURLtoUse = "\"\"" }

            var realtimeFinalURLtoUse : String = downloadURL ; if downloadURL.count < 4 { realtimeFinalURLtoUse = "\"\"" }

            if isInDebugMode { print("\t\tscheduleFinalURLtoUse || realtimeFinalURLtoUse : \(scheduleFinalURLtoUse) (\(scheduleFinalURLtoUse.count)) \(realtimeFinalURLtoUse) (\(realtimeFinalURLtoUse.count))") }
            
            // if dateFromCurrentLine == dateToFind { // ...the row has been added on the date we're looking for, process it.
                // if isInDebugMode { print("Found a valid date...") }
                
                if issue.contains(issueType.isAddNewFeed.rawValue) || issue.contains(issueType.isAddNewSource.rawValue) { // add new feed
                    
                    if datatype.contains(dataType.schedule.rawValue) { // add_gtfs_schedule_source

                        let authType : Int = authenticationType(for: authentication_type)

                        PYTHON_SCRIPT_ARGS_TEMP = "add_gtfs_schedule_source(provider=\"\(finalProvider)\", country_code=\"\(country)\", direct_download_url=\"\(scheduleFinalURLtoUse)\", authentication_type=\(authType), authentication_info_url=\"\(authentication_info_url)\", api_key_parameter_name=\"\(api_key_parameter_name)\", subdivision_name=\"\(subdivision_name)\", municipality=\"\(municipality)\", license_url=\"\(license_url)\", name=\"\(name)\", status=\"\(gtfsschedulestatus)\", features=\"\(gtfsschedulefeatures)\", feed_contact_email=\"\(feed_contact_email)\", redirects=\"\(redirects_array)\")"
                        
                    } else if datatype.contains(dataType.realtime.rawValue) { // add_gtfs_realtime_source
                        // Emma: entity_type matches the realtime Data type options of Vehicle Positions, Trip Updates, or Service Alerts. If one of those three are selected, add it. If not, omit it.
                        
                        let authType : Int = authenticationType(for: authentication_type)
                        let realtimecode : Array = realtimeCode(for:datatype)
                        let realtimecodeString: String = realtimecode.joined(separator:"\", \"")
                        // FIXME: Detect multiple entity types, forward as an array

                        PYTHON_SCRIPT_ARGS_TEMP = "add_gtfs_realtime_source(entity_type=[\"\(realtimecodeString)\"], provider=\"\(finalProvider)\", direct_download_url=\"\(realtimeFinalURLtoUse)\", authentication_type=\(authType), authentication_info_url=\"\(authentication_info_url)\", api_key_parameter_name=\"\(api_key_parameter_name)\", license_url=\"\(license_url)\", name=\"\(name)\", note=\"\(note)\", status=\"\(gtfsrealtimestatus)\", features=\"\(realtimefeatures)\", feed_contact_email=\"\(feed_contact_email)\", redirects=\"\(redirects_array)\")"
                        
                    }
                    
                } else if issue.contains(issueType.isUpdateExistingFeed.rawValue) { // update existing feed
                    
                    if datatype.contains(dataType.schedule.rawValue) { // update_gtfs_schedule_source
                        
                        let authType : Int = authenticationType(for: authentication_type)

                        PYTHON_SCRIPT_ARGS_TEMP = "update_gtfs_schedule_source(mdb_source_id=\(old_mbd_ID), provider=\"\(finalProvider)\", name=\"\(name)\", country_code=\"\(country)\", subdivision_name=\"\(subdivision_name)\", municipality=\"\(municipality)\", authentication_type=\(authType), authentication_info_url=\"\(authentication_info_url)\", api_key_parameter_name=\"\(api_key_parameter_name)\", status=\"\(gtfsschedulestatus)\", features=\"\(gtfsschedulefeatures)\", feed_contact_email=\"\(feed_contact_email)\", redirects=\"\(redirects_array)\")"
                        
                    } else if datatype.contains(dataType.realtime.rawValue) { // update_gtfs_realtime_source
                    
                        let authType : Int = authenticationType(for: authentication_type)
                        let realtimecode : Array = realtimeCode(for:datatype)
                        let realtimecodeString: String = realtimecode.joined(separator:"\", \"")

                        PYTHON_SCRIPT_ARGS_TEMP = "update_gtfs_realtime_source(mdb_source_id=\(old_mbd_ID), entity_type=[\"\(realtimecodeString)\"], provider=\"\(finalProvider)\", authentication_type=\(authType), authentication_info_url=\"\(authentication_info_url)\", api_key_parameter_name=\"\(api_key_parameter_name)\", name=\"\(name)\", note=\"\(note)\", status=\"\(gtfsrealtimestatus)\", features=\"\(realtimefeatures)\", feed_contact_email=\"\(feed_contact_email)\", redirects=\"\(redirects_array)\")"
                    }
                    
                }  else if issue.contains(issueType.isToRemoveFeed.rawValue) { // remove feed
                    
                    if datatype.contains(dataType.schedule.rawValue) { // update_gtfs_schedule_source
                        
                        let authType : Int = authenticationType(for: authentication_type)

                        PYTHON_SCRIPT_ARGS_TEMP = "update_gtfs_schedule_source(mdb_source_id=\(old_mbd_ID), provider=\"\(finalProvider)\", name=\"\"**** issueed for removal ****\"\", country_code=\"\(country)\", subdivision_name=\"\(subdivision_name)\", municipality=\"\(municipality)\", authentication_type=\(authType), authentication_info_url=\"\(authentication_info_url)\", api_key_parameter_name=\"\(api_key_parameter_name)\", status=\"\(gtfsschedulestatus)\", features=\"\(gtfsschedulefeatures)\", feed_contact_email=\"\(feed_contact_email)\", redirects=\"\(redirects_array)\")"
                        
                    } else if datatype.contains(dataType.realtime.rawValue) { // update_gtfs_realtime_source

                        let authType : Int = authenticationType(for: authentication_type)
                        let realtimecode : Array = realtimeCode(for:datatype)
                        let realtimecodeString: String = realtimecode.joined(separator:"\", \"")

                        PYTHON_SCRIPT_ARGS_TEMP = "update_gtfs_realtime_source(mdb_source_id=\(old_mbd_ID), entity_type=\"[\(realtimecodeString)]\", provider=\"\(finalProvider)\", authentication_type=\(authType), authentication_info_url=\"\(authentication_info_url)\", api_key_parameter_name=\"\(api_key_parameter_name)\", name=\"\"**** issueed for removal ****\"\", note=\"\(note)\", status=\"\(gtfsrealtimestatus)\", features=\"\(realtimefeatures)\", feed_contact_email=\"\(feed_contact_email)\", redirects=\"\(redirects_array)\")"
                        
                    }
                    
                } else { // ... assume this is a new feed by default :: add_gtfs_schedule_source

                    if datatype.contains(dataType.schedule.rawValue) { // add_gtfs_schedule_source
                        
                        let authType : Int = authenticationType(for: authentication_type)
                        PYTHON_SCRIPT_ARGS_TEMP = "add_gtfs_schedule_source(provider=\"\(finalProvider)\", country_code=\"\(country)\", direct_download_url=\"\(scheduleFinalURLtoUse)\", authentication_type=\(authType), authentication_info_url=\"\(authentication_info_url)\", api_key_parameter_name=\"\(api_key_parameter_name)\", subdivision_name=\"\(subdivision_name)\", municipality=\"\(municipality)\", license_url=\"\(license_url)\", name=\"\(name)\", status=\"\(gtfsschedulestatus)\", features=\"\(gtfsschedulefeatures)\", feed_contact_email=\"\(feed_contact_email)\", redirects=\"\(redirects_array)\")"
                        
                    } else if datatype.contains(dataType.realtime.rawValue) { // add_gtfs_schedule_source

                        let authType : Int = authenticationType(for: authentication_type)
                        let realtimecode : Array = realtimeCode(for: datatype)
                        let realtimecodeString: String = realtimecode.joined(separator:"\", \"")

                        PYTHON_SCRIPT_ARGS_TEMP = "add_gtfs_realtime_source(entity_type=[\"\(realtimecodeString)\"], provider=\"\(finalProvider)\", direct_download_url=\"\(realtimeFinalURLtoUse)\", authentication_type=\(authType), authentication_info_url=\"\(authentication_info_url)\", api_key_parameter_name=\"\(api_key_parameter_name)\", license_url=\"\(license_url)\", name=\"\(name)\", note=\"\(note)\", status=\"\(gtfsrealtimestatus)\", features=\"\(realtimefeatures)\", feed_contact_email=\"\(feed_contact_email)\", redirects=\"\(redirects_array)\")"
                        
                    }
                }
            }
            
        // } // END of the row has been added today, process it.

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
    print("Incorrect number of arguments provided to the script. Expected 4: a string with the URL, a date format and the date format desired.")
    exit(1)
}

// MARK: - FUNCTIONS

func extractDate(from theDateToConvert: String, usingGREP dateFormatAsGREP: Regex<AnyRegexOutput>, desiredDateFormat desiredFormat: String) -> String {
    if let match : Regex<Regex<AnyRegexOutput>.RegexOutput>.Match = theDateToConvert.firstMatch(of: dateFormatAsGREP) { 
        // find first match
        let matchOutput : String = String(match.output[0].substring!)

        // date formatter and find date
        let dateFormatter : DateFormatter = DateFormatter()
        dateFormatter.dateFormat = desiredFormat
        let date : Date? = dateFormatter.date(from: matchOutput)
        
        // default date if formatter fails, otherwise return correctly formatted date
        var returnDate : String = defaults.date.rawValue
        if date != nil { returnDate = dateFormatter.string(from: date!) }
        return returnDate
    }
    
    // return default date
    return defaults.date.rawValue
}

func authenticationType(for authString: String) -> Int {
    if authString.contains("0") { return 0 }
    if authString.contains("1") { return 1 }
    if authString.contains("2") { return 2 }
    return 0
}

func realtimeCode(for theDataType: String) -> [String] {
    var returnArray : [String] = []
    if theDataType.contains(realtimeEntityTypesString.vehiclePositions.rawValue) { returnArray.append(realtimeEntityTypes.vehiclePositions.rawValue)  }
    if theDataType.contains(realtimeEntityTypesString.tripUpdates.rawValue) { returnArray.append(realtimeEntityTypes.tripUpdates.rawValue) }
    if theDataType.contains(realtimeEntityTypesString.serviceAlerts.rawValue) { returnArray.append(realtimeEntityTypes.serviceAlerts.rawValue) }
    if returnArray.count < 1 { returnArray.append(realtimeEntityTypes.tripUpdates.rawValue) }
    return returnArray
}

func isURLPresent(in string: String) -> Bool {
    let pattern : String = #"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"#
    let range: Range<String.Index>? = string.range(of: pattern, options: .regularExpression)
    if range != nil { return true }
    return false
}

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
