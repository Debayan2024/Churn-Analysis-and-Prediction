param([ValidateSet('Inspect','Refresh','Save','Capture','Click','SetText')][string]$Action='Inspect',[string]$Name='',[string]$Value='')
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class PbiWindowCapture { [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdc, uint flags); }'
$root = [System.Windows.Automation.AutomationElement]::RootElement
$windows = $root.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)
$window = $null
foreach ($candidate in $windows) { if ($candidate.Current.Name -match '^ChurnDashboard') { $window=$candidate; break } }
if (-not $window) { throw 'ChurnDashboard window not found' }
Write-Output ('WINDOW: '+$window.Current.Name)
$elements=$window.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
if ($Action -eq 'Inspect') {
 foreach ($element in $elements) {
  if (-not $element.Current.IsOffscreen -and $element.Current.Name) { Write-Output ($element.Current.ControlType.ProgrammaticName+' | '+$element.Current.AutomationId+' | '+$element.Current.Name) }
 }
} elseif ($Action -eq 'Capture') {
 $bounds=$window.Current.BoundingRectangle
 $bitmap=New-Object System.Drawing.Bitmap ([int]$bounds.Width),([int]$bounds.Height)
 $graphics=[System.Drawing.Graphics]::FromImage($bitmap)
 $hdc=$graphics.GetHdc()
 $captured=[PbiWindowCapture]::PrintWindow([IntPtr]$window.Current.NativeWindowHandle,$hdc,2)
 $graphics.ReleaseHdc($hdc)
 if (-not $captured) {$graphics.Dispose();$bitmap.Dispose();throw "Power BI window capture failed"}
 $output=Join-Path $PSScriptRoot 'desktop-preview.png'
 $bitmap.Save($output,[System.Drawing.Imaging.ImageFormat]::Png)
 $graphics.Dispose();$bitmap.Dispose()
 Write-Output $output
} else {
 $targetName=if ($Action -eq 'Refresh') {'Refresh'} elseif ($Action -eq 'Save') {'Save'} else {$Name}
 $target=$null
 foreach ($element in $elements) {
  if (-not $element.Current.IsOffscreen -and $element.Current.IsEnabled -and $element.Current.Name -eq $targetName -and $element.Current.ControlType.ProgrammaticName -ne "ControlType.Text") { $target=$element; break }
 }
 if (-not $target) { throw ('Visible control not found: '+$targetName) }
 if ($Action -eq 'SetText') {
  $valuePattern=$target.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
  $valuePattern.SetValue($Value)
 } else {
  $pattern=$null
  if ($target.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$pattern)) {$pattern.Invoke()}
  elseif ($target.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern,[ref]$pattern)) {$pattern.Select()}
  elseif ($target.TryGetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern,[ref]$pattern)) {if ($pattern.Current.ExpandCollapseState -eq [System.Windows.Automation.ExpandCollapseState]::Expanded) {$pattern.Collapse()} else {$pattern.Expand()}}
  else {throw ('Control does not expose a supported action: '+$targetName)}
 }
 Write-Output ('Action completed: '+$Action+' '+$targetName)
}
