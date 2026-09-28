let
    Source = Table.SelectColumns(Customers, {"customerID", "Contract", "InternetService", "PhoneService", "MultipleLines", "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies", "PaperlessBilling", "PaymentMethod"}),
    Unpivoted = Table.UnpivotOtherColumns(Source, {"customerID"}, "Service", "Category"),
    Labels = Record.FromList({"Contract", "Internet service", "Phone service", "Multiple lines", "Online security", "Online backup", "Device protection", "Tech support", "Streaming TV", "Streaming movies", "Paperless billing", "Payment method"}, {"Contract", "InternetService", "PhoneService", "MultipleLines", "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies", "PaperlessBilling", "PaymentMethod"}),
    Renamed = Table.TransformColumns(Unpivoted, {{"Service", each Record.Field(Labels, _), type text}})
in
    Renamed