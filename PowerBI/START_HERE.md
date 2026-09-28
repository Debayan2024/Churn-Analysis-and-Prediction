# Your Power BI churn dashboard is ready

The project has been opened in Power BI Desktop, refreshed, checked and saved with its loaded data. All three report pages are working. You do not need to import the tables or create measures manually.

**Your next steps:** review the page tabs; adjust filters as needed; optionally use **File > Save as > Browse this device** and choose **Power BI Desktop file (*.pbix)** for a single-file copy. The delivered editable file is `ChurnDashboard.pbip`.

## Reopening the project or moving to another computer

1. Open `ChurnDashboard.pbip` in Power BI Desktop. Keep `ChurnDashboard.Report` and `ChurnDashboard.SemanticModel` alongside it.
2. If Power BI asks to enable project or enhanced report features, go to **File > Options and settings > Options > Preview features**. Enable **Power BI Project (.pbip) save option** and **Store reports using enhanced metadata format (PBIR)** if those options are present. Restart Desktop and reopen the project. Feature names/availability depend on the installed version. Use standard Power BI Desktop, not the Report Server edition.
3. Select **Home > Refresh**. The model definitions and visuals are already present; the first refresh imports the local CSV data. No Python execution or retraining is required.
4. If asked about privacy levels, assign the same appropriate level (for example, Organizational) to both local CSV sources. Do not disable privacy globally.
5. Verify the Overview shows **7,043 customers**, **1,869 churned**, **26.54% churn**, and **2,113 scored customers** with no slicers selected.
6. Review the three page tabs. **Service analysis** is saved with **Streaming movies** selected. Use **Choose service** to change it.
7. Save your working report. Use **File > Save as**, and choose **Power BI Desktop file (.pbix)** if you want a single shareable report file. The editable source remains this PBIP project.

## If the data location changes

Go to **Transform data > Edit parameters**, set **DataFolder** to the folder containing both original CSVs, and include a trailing `/` or `\`. It currently points to:

`D:/Projects/Churn-Analysis-and-Prediction-main/Data/`

The source files are `Telco-Customer-Churn.csv` and `results.csv`. Select **Close & Apply**, then **Refresh**. When moving the project to another computer, copy the original Data folder too. The fallback CSV is a snapshot and is not the PBIP project's refresh source.

## What is already built

- **Churn overview:** six KPI cards, contract/internet/gender/churn filters, a churn donut, gender counts, tenure churn proportions, monthly charges distribution, contract churn rates, top ten historical scores, and score coverage.
- **Customer risk list:** scored customers whose historical Churn label is No; risk/contract/internet/customer filters, top ten scores, risk-band counts, and a sorted customer table. Page filters can be edited in the Filters pane.
- **Service analysis:** a service selector and category churn charts, plus payment-method and internet-service churn rates. The service selector affects the two service-category charts; customer filters affect all charts.
- **Customers:** 7,043 original customer records, typed fields, blank TotalCharges cleaned to zero, left-joined prediction scores, readable risk bands and numeric bands.
- **Predictions:** 2,113 existing model scores, imported from results.csv. Hidden in report view to keep the field list simple.
- **CustomerServices:** 84,516 rows (12 services per customer) for the service selector. Measures use distinct customer counts, not raw service row counts.
- Two one-to-many relationships from Customers to Predictions and CustomerServices, plus 19 DAX measures and the purple/orange theme.

## Understand the numbers

- The original project scored only 2,113 customers. The remaining 4,930 keep a blank probability and a Not scored status. They are not treated as zero risk.
- Overview top-ten scores include historical churners. The worklist defaults to historical Churn = No and Scored: **1,539 customers**, including **26** with scores >=70% before additional filtering.
- High >=70%, Medium >=40% and <70%, Low <40% are report display rules, not validated business intervention thresholds. Change them in the Customers Power Query if needed.
- The dependents, partner and senior KPI cards report their shares **among churners**: 17.44%, 35.79%, and 25.47%. They are not the churn rate within those groups.
- The data is a historical snapshot, not live customer status. Refresh rereads CSVs; it does not retrain a model or create additional scores.
- Monthly charges and tenure are raw business values, not the standardized model features from results.csv. Tenure and charge distributions use readable 10-unit bands.

## Optional finishing touches in Desktop

- On Service analysis, Streaming movies is already selected. Change it if you prefer another service.
- If you want colored bars in the worklist, select its table > Format visual > Cell elements > choose Predicted Churn Probability > turn on Data bars; set minimum 0, maximum 1, and purple.
- Use the worklist's **... > Export data** to export the filtered customer list.
- Publish only if you want an online report and have a suitable Power BI workspace/license. Local-file scheduled refresh requires additional gateway/source setup; this project does not publish anything.

## Files for a manual fallback

If your Desktop version cannot open PBIP, update Desktop first. A manual rebuild is also possible:

- `Customers_PowerBI.csv`: clean, merged 7,043-row snapshot for Get data > Text/CSV. Rename the imported table Customers. Empty probabilities must remain null.
- `PowerQuery/*.pq`: complete queries to paste into blank queries in dependency order: DataFolder, Predictions, Customers, CustomerServices. This recreates the full three-table model more accurately than the snapshot.
- `Measures.dax`: add each measure separately with Modeling > New measure. Expressions are already included in the project; no copying is necessary when PBIP opens successfully.
- `TelecomChurn.theme.json`: View > Themes > Browse for themes.

## Validation and limitations

`data_validation.json` records verified source counts, joins and baseline metrics. `report_validation.json` records JSON-schema and field-reference validation. The project was also opened and refreshed in Power BI Desktop 2.157.1354.0. All three pages were checked, the service selector was exercised, and the loaded project was saved. See `desktop_validation.json` and `desktop-preview.png`. Schema validation describes the generated files before Desktop upgraded their format on save.

`build_dashboard.py` regenerates the authored project from the two original CSVs. Do not rerun it after making Desktop edits unless you intend to overwrite the generated report/model definitions. `validate_dashboard.py` requires jsonschema and fetches Microsoft's public schemas when not cached.

Sources: [Microsoft PBIP documentation](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview), [PBIR report format](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report), [semantic model format and first refresh](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset).
