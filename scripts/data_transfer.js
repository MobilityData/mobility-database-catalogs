
/*                                   Documentation for the DataTransferScript

        Overview

The `DataTransferScript` is an Apps Script designed to streamline the process of copying specific data from one Google Sheets tab ("Raw data") to another ("[CLEANED] For import") in the ‘[Public] OpenMobilityData source updates’ google sheet  and then updating  column C in the ("[CLEANED] For import") tab based on conditions set. The script consists of two main functions: `copyData` and `updateDates`.

       Script Functions

1. DataTransferScript():
Purpose: This function serves as the main function that calls the other two functions: `copyData` and `updateDates`.

  Function Calls:
     copyData(): Copies selected data from the "Raw data" tab to the "[CLEANED] For import" tab in the ‘[Public] OpenMobilityData source updates’ google sheet.
     updateDates() : Updates dates in column B of the "[CLEANED] For import" tab based on the presence of data in column C in the ‘[Public] OpenMobilityData source updates’ google sheet.

2. copyData():

   Purpose: Copies data from specific columns in the "Raw data" tab to corresponding columns in the "[CLEANED] For import" tab based on a user-specified row range.

   Expected Inputs:
User input for the row range (e.g., a single row like 5 or a range like 3:10).

  Expected Outputs:
     		Data from the selected rows and specified columns in the "Raw data" tab is copied to the corresponding columns in the "[CLEANED] For import" tab. 


3. updateDates():

   Purpose: Updates the date in column B of the "[CLEANED] For import" tab if the corresponding cell in column C is not empty.

  Expected Inputs:
     		The function operates on the data present in columns B and C of the active sheet.

    Expected Inputs:
     		Column B is updated with the current date if the corresponding cell in column C has a value. If column C is empty, the corresponding cell in column B is cleared.


      How to run the script:

1. Open the ‘[Public] OpenMobilityData source updates’ google sheet.
2. Go to the "[CLEANED] For import" tab.
3. Click on the “Data Transfer” button.
4. Input desired row number or range you want to copy from the ("Raw data") tab.
5. The `DataTransferScript` validates the input and converts it into a list of row numbers.
6. Specific columns are copied from the source tab ("Raw data") to the destination tab ("[CLEANED] For import") based on the user's input.
7. The copied data is pasted into the appropriate columns starting from the first available row in the destination tab.
8. The `updateDates()` function is called to update the dates in column B of the "[CLEANED] For import" tab based on the presence of data in column C.
 9. The `updateDates() script iterates through all rows starting from row 2 (to avoid the header)
10. It checks if each cell in column C has a value.
 11. If a value exists, the corresponding cell in column B is updated with the current date.
 12. If no value exists in column C, the corresponding cell in column B is cleared.

*/


//                               Running the Script Code


function DataTransferScript() {
    
  copyData();

  // Update dates based on column C
  updateDates();
}

function copyData() {
  // Get the spreadsheet and source/destination tabs
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  var sourceSheet = spreadsheet.getSheetByName("Raw data");
  var destinationSheet = spreadsheet.getSheetByName("[CLEANED] For import");

  // Get user input for row range
  var ui = SpreadsheetApp.getUi();
  var response = ui.prompt('Enter row number or range (e.g., 5 or 3:10):', ui.ButtonSet.OK_CANCEL);

  if (response.getSelectedButton() == ui.Button.CANCEL) {
    return;
  }

  var rowRange = response.getResponseText();

  // Convert row range to numbers
  var rowNumbers = [];
  try {
    if (rowRange.includes(":")) {
      var rangeParts = rowRange.split(":");
      var startRow = parseInt(rangeParts[0]);
      var endRow = parseInt(rangeParts[1]);
      for (var i = startRow; i <= endRow; i++) {
        rowNumbers.push(i);
      }
    } else {
      rowNumbers.push(parseInt(rowRange));
    }
  } catch (error) {
    Browser.msgBox("Invalid row range format. Please enter a valid row number or range (e.g., 5 or 3:10).");
    return;
  }

  // columns to copy
  var sourceColumns = [3,7,8,9,10,11,12,13,15,19,20,21,22,26,29]; // columns C, F, H, J
  var destinationColumns = [3,7,8,9,10,11,12,13,15,19,20,21,22,26,30]; // Matching destination columns

  // Validation of column arrays
  if (sourceColumns.length !== destinationColumns.length) {
    Browser.msgBox("Error: Source and destination column arrays must have the same length.");
    return;
  }

  // Creation of array to hold the values to be copied
  var valuesToCopy = [];

  // loop over rows and extract values for each column specified
  for (var i = 0; i < rowNumbers.length; i++) {
    var row = rowNumbers[i];
    var rowValues = [];
    for (var j = 0; j < sourceColumns.length; j++) {
      var sourceColumn = sourceColumns[j];
      rowValues.push(sourceSheet.getRange(row, sourceColumn).getValue());
    }
    valuesToCopy.push(rowValues);
  }

  // Starting row for the destination range
  var destinationStartRow = destinationSheet.getLastRow() + 1;
  
  // loop to paste the values into the correct destination columns
  for (var k = 0; k < destinationColumns.length; k++) {
    var colValues = valuesToCopy.map(function(row) {
      return [row[k]]; 
    });
    var destinationColumn = destinationColumns[k];
    destinationSheet.getRange(destinationStartRow, destinationColumn, colValues.length, 1).setValues(colValues);
  }
}
//  function to update column B with current dates based on column C
function updateDates() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var lastRow = sheet.getLastRow(); 
  var columnC = sheet.getRange("C2:C" + lastRow).getValues(); 
  var currentDate = new Date(); // Get today's date
  
  for (var i = 0; i < columnC.length; i++) {
    var rowIndex = i + 2; 
    var targetCell = sheet.getRange(rowIndex, 2); 
    if (columnC[i][0] !== "") { 
      targetCell.setValue(currentDate); 
    } else {
      targetCell.clear(); // Clear the cell in column B if the corresponding cell in column C is empty
    }
  }
}