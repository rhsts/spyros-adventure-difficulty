# Dismiss Dolphin's SSL (clientca.pem) warning if it is showing; print any other warning text.
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$ae = [System.Windows.Automation.AutomationElement]; $S = [System.Windows.Automation.TreeScope]
$w = $ae::RootElement.FindFirst($S::Descendants, (New-Object System.Windows.Automation.PropertyCondition($ae::NameProperty, "Warning")))
if (-not $w) { "no warning"; exit }
$txt = ($w.FindAll($S::Descendants, [System.Windows.Automation.Condition]::TrueCondition) | Where-Object { $_.Current.ControlType.ProgrammaticName -eq "ControlType.Text" } | ForEach-Object { $_.Current.Name }) -join " "
if ($txt -like "*clientca.pem*") {
  $b = $w.FindFirst($S::Descendants, (New-Object System.Windows.Automation.PropertyCondition($ae::NameProperty, "Ignore for this session")))
  $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); "dismissed SSL warning"
} else { "other warning: $txt" }
