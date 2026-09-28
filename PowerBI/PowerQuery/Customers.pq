let
    Source = Csv.Document(File.Contents(DataFolder & "Telco-Customer-Churn.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TotalChargesClean = Table.TransformColumns(Headers, {{"TotalCharges", each if _ = null or Text.Trim(_) = "" then 0 else Number.FromText(_, "en-US"), type number}}),
    Typed = Table.TransformColumnTypes(TotalChargesClean, {{"customerID", type text}, {"gender", type text}, {"SeniorCitizen", Int64.Type}, {"Partner", type text}, {"Dependents", type text}, {"tenure", Int64.Type}, {"PhoneService", type text}, {"MultipleLines", type text}, {"InternetService", type text}, {"OnlineSecurity", type text}, {"OnlineBackup", type text}, {"DeviceProtection", type text}, {"TechSupport", type text}, {"StreamingTV", type text}, {"StreamingMovies", type text}, {"Contract", type text}, {"PaperlessBilling", type text}, {"PaymentMethod", type text}, {"MonthlyCharges", type number}, {"Churn", type text}}, "en-US"),
    Joined = Table.NestedJoin(Typed, {"customerID"}, Predictions, {"customerID"}, "Prediction", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Joined, "Prediction", {"ChurnProb"}, {"ChurnProbability"}),
    Scored = Table.AddColumn(Expanded, "Prediction Status", each if [ChurnProbability] = null then "Not scored" else "Scored", type text),
    Risk = Table.AddColumn(Scored, "Risk Band", each if [ChurnProbability] = null then "Not scored" else if [ChurnProbability] >= 0.7 then "High" else if [ChurnProbability] >= 0.4 then "Medium" else "Low", type text),
    Senior = Table.AddColumn(Risk, "Senior Citizen", each if [SeniorCitizen] = 1 then "Yes" else "No", type text),
    TenureStart = Table.AddColumn(Senior, "Tenure Band Sort", each Number.IntegerDivide([tenure], 10) * 10, Int64.Type),
    TenureBand = Table.AddColumn(TenureStart, "Tenure Band", each Text.From([Tenure Band Sort]) & "-" & Text.From([Tenure Band Sort] + 9), type text),
    ChargeStart = Table.AddColumn(TenureBand, "Monthly Charge Band Sort", each Number.IntegerDivide([MonthlyCharges], 10) * 10, Int64.Type),
    ChargeBand = Table.AddColumn(ChargeStart, "Monthly Charge Band", each Text.From([Monthly Charge Band Sort]) & "-" & Text.From([Monthly Charge Band Sort] + 9), type text)
in
    ChargeBand