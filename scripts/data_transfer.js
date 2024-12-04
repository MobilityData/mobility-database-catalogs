function combinedScript() {
    
    copyDataToCleanedTab();
  
    // Update dates based on column C
    updateDatesBasedOnColumnC();
}

function copyDataToCleanedTab() {
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

function updateDatesBasedOnColumnC() {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet(); // Get the active sheet
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
