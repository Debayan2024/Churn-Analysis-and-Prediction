"""Build the local Power BI project from the original CSVs. Standard library only."""
import csv, json, uuid, hashlib
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'PowerBI'
REPORT = OUT / 'ChurnDashboard.Report'
MODEL = OUT / 'ChurnDashboard.SemanticModel'
DEF = REPORT / 'definition'
SCHEMA = 'https://developer.microsoft.com/json-schemas/fabric/'
PURPLE, ORANGE, INK, MUTED, BG = '#6366FF', '#FF4B16', '#252942', '#6B7280', '#F2F3F7'

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n' if not isinstance(value,str) else value, encoding='utf-8')
def sid(name): return hashlib.sha256(name.encode()).hexdigest()[:20]
def schema(part, version='1.0.0'): return SCHEMA + 'item/report/definition/' + part + '/' + version + '/schema.json'
def literal(value):
    if isinstance(value,bool): val = 'true' if value else 'false'
    elif isinstance(value,(int,float)): val = str(value) + 'D'
    else: val = "'" + str(value).replace("'", "''") + "'"
    return {'expr': {'Literal': {'Value': val}}}
def color(value): return {'solid': {'color': literal(value)}}
def obj(**props): return [{'properties':props}]
def field(table, name, measure=False):
    return {('Measure' if measure else 'Column'): {'Expression': {'SourceRef': {'Entity':table}}, 'Property':name}}
def col(name,table='Customers'): return field(table,name)
def meas(name): return field('Customers',name,True)
def projection(f):
    val = next(iter(f.values())); name=val['Property']; table=val['Expression']['SourceRef']['Entity']
    return {'field':f,'queryRef':table+'.'+name,'nativeQueryRef':name}

with (ROOT/'Data/Telco-Customer-Churn.csv').open(newline='',encoding='utf-8-sig') as f:
    raw=list(csv.DictReader(f))
with (ROOT/'Data/results.csv').open(newline='',encoding='utf-8-sig') as f:
    predictions=list(csv.DictReader(f))
ids={r['customerID'] for r in raw}
assert len(ids)==len(raw), 'Duplicate customer IDs'
scores={r['customerID']:float(r['ChurnProb']) for r in predictions}
assert len(scores)==len(predictions), 'Duplicate prediction IDs'
assert set(scores)<=ids, 'Prediction IDs missing from source data'
assert all(0<=p<=1 for p in scores.values()), 'Invalid probability'

# Native Power Query imports: original files stay the source of truth.
datafolder=str(ROOT/'Data').replace('\\','/')+'/'
parameter='"'+datafolder+'" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'
prediction_m="""let
    Source = Csv.Document(File.Contents(DataFolder & "results.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Selected = Table.SelectColumns(Headers, {"customerID", "ChurnProb"}),
    Typed = Table.TransformColumnTypes(Selected, {{"customerID", type text}, {"ChurnProb", type number}}, "en-US")
in
    Typed"""
customer_m="""let
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
    ChargeBand"""
services=['Contract','InternetService','PhoneService','MultipleLines','OnlineSecurity','OnlineBackup','DeviceProtection','TechSupport','StreamingTV','StreamingMovies','PaperlessBilling','PaymentMethod']
service_names={'InternetService':'Internet service','PhoneService':'Phone service','MultipleLines':'Multiple lines','OnlineSecurity':'Online security','OnlineBackup':'Online backup','DeviceProtection':'Device protection','TechSupport':'Tech support','StreamingTV':'Streaming TV','StreamingMovies':'Streaming movies','PaperlessBilling':'Paperless billing','PaymentMethod':'Payment method','Contract':'Contract'}
service_m='let\n    Source = Table.SelectColumns(Customers, {"customerID", '+', '.join('"'+x+'"' for x in services)+'}),\n    Unpivoted = Table.UnpivotOtherColumns(Source, {"customerID"}, "Service", "Category"),\n    Labels = Record.FromList({'+', '.join('"'+service_names[x]+'"' for x in services)+'}, {'+', '.join('"'+x+'"' for x in services)+'}),\n    Renamed = Table.TransformColumns(Unpivoted, {{"Service", each Record.Field(Labels, _), type text}})\nin\n    Renamed'

measures=[]
def metric(name, expression, fmt='#,0', folder='Overview', description=''):
    measures.append({'name':name,'expression':expression,'formatString':fmt,'displayFolder':folder,'description':description or name})
metric('Total Customers','COUNTROWS(Customers)')
metric('Churned Customers','CALCULATE([Total Customers], KEEPFILTERS(Customers[Churn] = "Yes"))')
metric('Retained Customers','CALCULATE([Total Customers], KEEPFILTERS(Customers[Churn] = "No"))')
metric('Churn Rate','DIVIDE([Churned Customers], [Total Customers])','0.00%')
for title,column in [('Dependents','Dependents'),('Partner','Partner'),('Senior Citizens','Senior Citizen')]:
    metric('Churners with '+title,'DIVIDE(CALCULATE([Churned Customers], KEEPFILTERS(Customers['+column+'] = "Yes")), [Churned Customers])','0.00%',description='Share of churners who have this attribute; not the churn rate within that group.')
metric('Average Monthly Charges','AVERAGE(Customers[MonthlyCharges])','#,0.00')
metric('Scored Customers','CALCULATE([Total Customers], KEEPFILTERS(Customers[Prediction Status] = "Scored"))',folder='Prediction coverage')
metric('Score Coverage','DIVIDE([Scored Customers], [Total Customers])','0.00%','Prediction coverage')
metric('High Risk Customers','CALCULATE([Scored Customers], KEEPFILTERS(Customers[Risk Band] = "High"))',folder='Risk')
metric('Predicted Churn Probability','MAX(Customers[ChurnProbability])','0.00%','Risk','Existing saved model probability, blank for customers without a score. In a customer row this is that customer\'s score.')
metric('Average Churn Probability','AVERAGE(Customers[ChurnProbability])','0.00%','Risk')
metric('Customer Monthly Charges','IF(HASONEVALUE(Customers[customerID]), MAX(Customers[MonthlyCharges]))','#,0.00','Risk')
metric('Customer Tenure Months','IF(HASONEVALUE(Customers[customerID]), MAX(Customers[tenure]))','0','Risk')
metric('Top 10 Churn Probability', 'VAR Candidates = FILTER(ALLSELECTED(Customers[customerID]), NOT ISBLANK(CALCULATE([Predicted Churn Probability])))\nVAR TopCustomers = TOPN(10, Candidates, [Predicted Churn Probability], DESC, Customers[customerID], ASC)\nRETURN IF(HASONEVALUE(Customers[customerID]) && CONTAINS(TopCustomers, Customers[customerID], SELECTEDVALUE(Customers[customerID])), [Predicted Churn Probability])','0.00%','Risk','Exactly ten scored customers at most, ordered by probability then customer ID to resolve ties.')
metric('Service Customers','DISTINCTCOUNT(CustomerServices[customerID])',folder='Service analysis')
metric('Service Churned Customers','CALCULATE([Service Customers], KEEPFILTERS(Customers[Churn] = "Yes"))',folder='Service analysis')
metric('Service Churn Rate','DIVIDE([Service Churned Customers], [Service Customers])','0.00%','Service analysis')

numeric={'SeniorCitizen':'int64','tenure':'int64','MonthlyCharges':'double','TotalCharges':'double','ChurnProbability':'double','Tenure Band Sort':'int64','Monthly Charge Band Sort':'int64'}
customer_columns=list(raw[0])+['ChurnProbability','Prediction Status','Risk Band','Senior Citizen','Tenure Band Sort','Tenure Band','Monthly Charge Band Sort','Monthly Charge Band']
def model_column(name,dt='string'):
    c={'name':name,'dataType':dt,'sourceColumn':name,'summarizeBy':'none'}
    if dt=='double': c['formatString']='0.00%' if name in ['ChurnProb','ChurnProbability'] else '#,0.00'
    if dt=='int64': c['formatString']='0'
    if name.endswith(' Sort') or name=='SeniorCitizen':c['isHidden']=True
    if name in ['Tenure Band','Monthly Charge Band']:c['sortByColumn']=name+' Sort'
    return c

def table(name,columns,expression,hidden=False):
    return {'name':name,'isHidden':hidden,'columns':columns,'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':expression.splitlines()}}]}
ct=table('Customers',[model_column(n,numeric.get(n,'string')) for n in customer_columns],customer_m)
ct['columns'][0]['isKey']=True
ct['measures']=measures
pt=table('Predictions',[model_column('customerID'),model_column('ChurnProb','double')],prediction_m,True)
st=table('CustomerServices',[model_column(x) for x in ['customerID','Service','Category']],service_m)
model={'name':'ChurnDashboard','compatibilityLevel':1567,'model':{'culture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','sourceQueryCulture':'en-US','dataAccessOptions':{'legacyRedirects':True,'returnErrorValuesAsNull':True},'expressions':[{'name':'DataFolder','kind':'m','expression':parameter}],'tables':[ct,pt,st],'relationships':[{'name':'Predictions_Customers','fromTable':'Predictions','fromColumn':'customerID','toTable':'Customers','toColumn':'customerID','fromCardinality':'many','toCardinality':'one','crossFilteringBehavior':'oneDirection'},{'name':'Services_Customers','fromTable':'CustomerServices','fromColumn':'customerID','toTable':'Customers','toColumn':'customerID','fromCardinality':'many','toCardinality':'one','crossFilteringBehavior':'oneDirection'}],'annotations':[{'name':'PBI_QueryOrder','value':json.dumps(['DataFolder','Predictions','Customers','CustomerServices'])},{'name':'__PBI_TimeIntelligenceEnabled','value':'0'}]}}
write(MODEL/'model.bim',model)
write(MODEL/'definition.pbism',{'$schema':SCHEMA+'item/semanticModel/definitionProperties/1.0.0/schema.json','version':'1.0','settings':{'qnaEnabled':False}})
write(OUT/'ChurnDashboard.pbip',{'$schema':SCHEMA+'pbip/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':'ChurnDashboard.Report'}}],'settings':{'enableAutoRecovery':True}})
write(REPORT/'definition.pbir',{'$schema':SCHEMA+'item/report/definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':'../ChurnDashboard.SemanticModel'}}})
write(DEF/'version.json',{'$schema':schema('versionMetadata'),'version':'2.0.0'})
theme={'name':'Telecom Churn','dataColors':[PURPLE,ORANGE,'#22A699','#F5B841','#8C6DDF','#47A7DD'],'background':'#FFFFFF','foreground':INK,'tableAccent':PURPLE,'textClasses':{'title':{'fontFace':'Segoe UI Semibold','fontSize':13,'color':INK},'label':{'fontFace':'Segoe UI','fontSize':10,'color':MUTED},'callout':{'fontFace':'Segoe UI Semibold','fontSize':30,'color':INK}}}
write(REPORT/'StaticResources/RegisteredResources/TelecomChurn.json',theme)
write(OUT/'TelecomChurn.theme.json',theme)
write(DEF/'report.json',{'$schema':schema('report','2.0.0'),'themeCollection':{'customTheme':{'name':'TelecomChurn','reportVersionAtImport':'2.0.0','type':'RegisteredResources'}},'resourcePackages':[{'name':'RegisteredResources','type':'RegisteredResources','items':[{'name':'TelecomChurn','path':'TelecomChurn.json','type':'CustomTheme'}]}],'settings':{'useStylableVisualContainerHeader':True,'defaultFilterActionIsDataFilter':True,'defaultDrillFilterOtherVisuals':True,'allowChangeFilterTypes':True}})

# PBIR native report visuals, with no custom visual dependencies.
page_ids=[]
visual_count=0

def categorical_filter(table,column,value):
    return {'name':sid(table+column+value),'field':field(table,column),'type':'Categorical','filter':{'Version':2,'From':[{'Name':'s','Entity':table,'Type':0}],'Where':[{'Condition':{'In':{'Expressions':[{'Column':{'Expression':{'SourceRef':{'Source':'s'}},'Property':column}}],'Values':[[{'Literal':{'Value':"'"+value.replace("'","''")+"'"}}]]}}}]},'howCreated':'User'}

def page(name,title,height=1000,filters=None):
    pid=sid(name); page_ids.append(pid)
    p={'$schema':schema('page'),'name':pid,'displayName':title,'displayOption':'FitToPage','height':height,'width':1600,'objects':{'background':obj(color=color(BG),transparency=literal(0))}}
    if filters:p['filterConfig']={'filters':filters}
    write(DEF/'pages'/pid/'page.json',p)
    return pid

def visual(pid,name,kind,x,y,w,h,title=None,roles=None,objects=None,sort=None,filters=None):
    global visual_count
    visual_count+=1
    v={'visualType':kind,'drillFilterOtherVisuals':True,'visualContainerObjects':{'background':obj(show=literal(True),color=color('#FFFFFF'),transparency=literal(0)),'border':obj(show=literal(True),color=color('#E2E5EE'),radius=literal(8))}}
    if title:v['visualContainerObjects']['title']=obj(show=literal(True),text=literal(title),fontColor=color(INK),fontSize=literal(12),bold=literal(True),fontFamily=literal('Segoe UI'))
    if roles:
        v['query']={'queryState':{role:{'projections':[projection(f) for f in fields]} for role,fields in roles.items()}}
        if sort:v['query']['sortDefinition']={'sort':[{'field':sort[0],'direction':sort[1]}],'isDefaultSort':False}
    if objects:v['objects']=objects
    data={'$schema':schema('visualContainer','2.1.0'),'name':sid(pid+name),'position':{'x':x,'y':y,'width':w,'height':h,'z':visual_count*1000,'tabOrder':visual_count*1000},'visual':v}
    if filters:data['filterConfig']={'filters':filters}
    write(DEF/'pages'/pid/'visuals'/data['name']/'visual.json',data)

def text(pid,name,text,x,y,w,h,size=12,fg=MUTED):
    objects={'general':[{'properties':{'paragraphs':[{'textRuns':[{'value':text,'textStyle':{'fontFamily':'Segoe UI','fontSize':str(size)+'pt','color':fg}}]}]}}]}
    visual(pid,name,'textbox',x,y,w,h,objects=objects)

def card(pid,name,title,x,y,w=246,h=104,accent=PURPLE):
    visual(pid,name,'card',x,y,w,h,title,{'Values':[meas(name)]},{'labels':obj(color=color(accent),fontSize=literal(28),labelDisplayUnits=literal(0)),'categoryLabels':obj(show=literal(False))})

def slicer(pid,name,title,x,y,w=374,h=76,table='Customers'):
    visual(pid,name+title,'slicer',x,y,w,h,title,{'Values':[col(name,table)]},{'data':obj(mode=literal('Dropdown')),'selection':obj(singleSelect=literal(False))})

def chart(pid,name,kind,x,y,w,h,title,category,measure='Total Customers',series=None,sort=None,extra=None):
    roles={'Category':[category],'Y':[meas(measure)]}
    if series:roles['Series']=[series]
    objects={'labels':obj(show=literal(True),fontSize=literal(10),labelDisplayUnits=literal(0)),'legend':obj(show=literal(series is not None),position=literal('Top')),'categoryAxis':obj(showAxisTitle=literal(False)),'valueAxis':obj(showAxisTitle=literal(False))}
    if extra:objects.update(extra)
    visual(pid,name,kind,x,y,w,h,title,roles,objects,sort=sort or (meas(measure),'Descending'))

p=page('overview','01 | Churn overview')
text(p,'heading','TELECOM  |  CHURN DASHBOARD',24,18,1552,55,26,INK)
text(p,'intro','Explore historical churn, customer segments and the existing model scores. Purple: retained / Orange: churned.',24,80,1552,35,11)
for i,(m,t) in enumerate([('Total Customers','TOTAL CUSTOMERS'),('Churned Customers','CHURNED CUSTOMERS'),('Churn Rate','CHURN RATE'),('Churners with Dependents','CHURNERS WITH DEPENDENTS'),('Churners with Partner','CHURNERS WITH A PARTNER'),('Churners with Senior Citizens','CHURNERS WHO ARE SENIORS')]):
    card(p,m,t,24+i*262,130,242,110,ORANGE if i in [1,2] else PURPLE)
for i,(n,t) in enumerate([('Contract','Contract'),('InternetService','Internet service'),('gender','Gender'),('Churn','Historical churn')]):slicer(p,n,t,24+i*393,257,373)
visual(p,'distribution','donutChart',24,350,300,282,'Churn distribution',{'Category':[col('Churn')],'Y':[meas('Total Customers')]},{'legend':obj(show=literal(True),position=literal('Bottom')),'labels':obj(show=literal(True),labelStyle=literal('Percent of total'))},sort=(col('Churn'),'Ascending'))
chart(p,'gender','clusteredColumnChart',342,350,330,282,'Customers by gender',col('gender'),series=col('Churn'),sort=(col('gender'),'Ascending'))
chart(p,'tenure','hundredPercentStackedColumnChart',690,350,432,282,'Churn mix by tenure (months)',col('Tenure Band'),series=col('Churn'),sort=(col('Tenure Band'),'Ascending'))
chart(p,'charges','columnChart',1140,350,436,282,'Monthly charges distribution',col('Monthly Charge Band'),series=col('Churn'),sort=(col('Monthly Charge Band'),'Ascending'))
chart(p,'contract','clusteredColumnChart',24,650,430,286,'Churn rate by contract',col('Contract'),'Churn Rate')
chart(p,'top10','barChart',472,650,760,286,'Top 10 scores | historical sample',col('customerID'),'Top 10 Churn Probability')
card(p,'Scored Customers','CUSTOMERS WITH A SCORE',1250,650,326,133)
card(p,'Score Coverage','PREDICTION COVERAGE',1250,801,326,135)
text(p,'foot','Scores are available for 2,113 of 7,043 customers. Blank scores mean not scored. For outreach, use the Customer risk list page, filtered to historical Churn = No.',24,953,1552,33,10)

p=page('risk','02 | Customer risk list',1000,[categorical_filter('Customers','Churn','No'),categorical_filter('Customers','Prediction Status','Scored')])
text(p,'heading','CUSTOMER RISK  |  RETENTION WORKLIST',24,18,1552,55,26,INK)
text(p,'intro','Default scope: scored customers whose historical Churn label is No. Scores are from the saved project, not live customer status.',24,80,1552,35,11)
for i,(m,t) in enumerate([('Scored Customers','SCORED CUSTOMERS IN SCOPE'),('High Risk Customers','HIGH RISK | SCORE >= 70%'),('Average Churn Probability','AVERAGE CHURN PROBABILITY'),('Average Monthly Charges','AVERAGE MONTHLY CHARGES')]):card(p,m,t,24+i*393,132,373,110)
for i,(n,t) in enumerate([('Risk Band','Risk band'),('Contract','Contract'),('InternetService','Internet service'),('customerID','Customer ID')]):slicer(p,n,t,24+i*393,260,373)
chart(p,'priority','barChart',24,354,800,260,'Top 10 scores in the selected segment',col('customerID'),'Top 10 Churn Probability')
chart(p,'riskmix','clusteredColumnChart',842,354,734,260,'Customers by risk band',col('Risk Band'))
visual(p,'worklist','tableEx',24,632,1552,297,'Customer worklist | sorted by probability',{'Values':[col('customerID'),col('gender'),col('Senior Citizen'),col('Contract'),col('InternetService'),col('Partner'),col('Dependents'),meas('Customer Tenure Months'),meas('Customer Monthly Charges'),col('Risk Band'),meas('Predicted Churn Probability')]},{'grid':obj(gridVertical=literal(False),gridHorizontal=literal(True),rowPadding=literal(6)),'columnHeaders':obj(fontSize=literal(10),fontColor=color(INK),backColor=color('#F0F0FF')),'values':obj(fontSize=literal(10)),'total':obj(totals=literal(False))},sort=(meas('Predicted Churn Probability'),'Descending'))
text(p,'foot','Risk bands are adjustable report rules: High >= 70%; Medium >= 40% and < 70%; Low < 40%. They are not model-validated intervention thresholds. Export the table using its ... menu.',24,948,1552,43,10)

p=page('services','03 | Service analysis')
text(p,'heading','CUSTOMER SERVICES  |  CHURN DRIVERS',24,18,1552,55,26,INK)
text(p,'intro','Select one service to compare churn across its categories. If multiple services are selected, the category chart uses distinct customers across those services.',24,80,1552,42,11)
slicer(p,'Service','Choose service',24,140,540,92,'CustomerServices')
slicer(p,'Contract','Contract',582,140,488,92)
slicer(p,'InternetService','Internet service',1088,140,488,92)
chart(p,'service_churn','clusteredColumnChart',24,251,950,330,'Churn rate by selected service category',col('Category','CustomerServices'),'Service Churn Rate')
chart(p,'service_mix','clusteredColumnChart',992,251,584,330,'Customer count by service category',col('Category','CustomerServices'),'Service Customers',series=col('Churn'))
chart(p,'payment','barChart',24,600,760,313,'Churn rate by payment method',col('PaymentMethod'),'Churn Rate')
chart(p,'internet','clusteredColumnChart',802,600,774,313,'Churn rate by internet service',col('InternetService'),'Churn Rate')
text(p,'foot','Service selection changes the two service-category charts. Contract and Internet service filter all charts on this page. Associations in historical data do not establish why an individual customer churned.',24,936,1552,52,10)
write(DEF/'pages/pages.json',{'$schema':schema('pagesMetadata'),'pageOrder':page_ids,'activePageName':page_ids[0]})

# Friendly fallback exports and a reusable plain-text query/measure reference.
export_fields=list(raw[0])+['ChurnProbability','Prediction Status','Risk Band']
with (OUT/'Customers_PowerBI.csv').open('w',newline='',encoding='utf-8-sig') as f:
    writer=csv.DictWriter(f,fieldnames=export_fields);writer.writeheader()
    for row in raw:
        r=dict(row);r['TotalCharges']=float(r['TotalCharges'].strip() or 0)
        score=scores.get(r['customerID']);r.update({'ChurnProbability':score if score is not None else '', 'Prediction Status':'Scored' if score is not None else 'Not scored','Risk Band':'Not scored' if score is None else 'High' if score>=.7 else 'Medium' if score>=.4 else 'Low'})
        writer.writerow(r)
write(OUT/'PowerQuery/DataFolder.pq',parameter)
write(OUT/'PowerQuery/Predictions.pq',prediction_m)
write(OUT/'PowerQuery/Customers.pq',customer_m)
write(OUT/'PowerQuery/CustomerServices.pq',service_m)
write(OUT/'Measures.dax','// Measures already included in the model. Add individually only for a manual rebuild.\n\n'+'\n\n'.join(m['name']+' =\n'+m['expression'] for m in measures)+'\n')
churned=[r for r in raw if r['Churn']=='Yes']
active=[r for r in raw if r['Churn']=='No' and r['customerID'] in scores]
checks={'source_customers':len(raw),'historical_churned':len(churned),'historical_churn_rate':len(churned)/len(raw),'blank_TotalCharges_replaced_with_zero':sum(not r['TotalCharges'].strip() for r in raw),'scored_customers':len(scores),'unscored_customers':len(raw)-len(scores),'prediction_coverage':len(scores)/len(raw),'churners_with_dependents':sum(r['Dependents']=='Yes' for r in churned)/len(churned),'churners_with_partner':sum(r['Partner']=='Yes' for r in churned)/len(churned),'churners_who_are_seniors':sum(r['SeniorCitizen']=='1' for r in churned)/len(churned),'default_worklist_customers':len(active),'default_worklist_high_risk':sum(scores[r['customerID']]>=.7 for r in active),'service_rows':len(raw)*len(services),'pages':len(page_ids),'visuals':visual_count,'measures':len(measures),'max_score':max(scores.values()),'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'Data/Telco-Customer-Churn.csv',ROOT/'Data/results.csv']}}
write(OUT/'data_validation.json',checks)
write(OUT/'.gitignore','**/.pbi/\nvalidation-cache/\n*.pbix\n')
print(json.dumps(checks,indent=2))
print('Created',OUT/'ChurnDashboard.pbip')
