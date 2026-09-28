let
    Source = Csv.Document(File.Contents(DataFolder & "results.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Selected = Table.SelectColumns(Headers, {"customerID", "ChurnProb"}),
    Typed = Table.TransformColumnTypes(Selected, {{"customerID", type text}, {"ChurnProb", type number}}, "en-US")
in
    Typed