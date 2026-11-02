# Boot Spyro's Adventure in Dolphin and dismiss only the known SSL warning.
# Usage: powershell -File boot.ps1 -Dolphin PATH\Dolphin.exe -Game PATH\game.rvz
param([Parameter(Mandatory)][string]$Dolphin, [Parameter(Mandatory)][string]$Game)
Start-Process $Dolphin -ArgumentList '-e', ('"' + $Game + '"')
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$ae = [System.Windows.Automation.AutomationElement]; $S = [System.Windows.Automation.TreeScope]
for ($i = 0; $i -lt 60; $i++) {
  Start-Sleep -Seconds 1
  $w = $ae::RootElement.FindFirst($S::Descendants, (New-Object System.Windows.Automation.PropertyCondition($ae::NameProperty, "Warning")))
  if ($w) {
    $txt = ($w.FindAll($S::Descendants, [System.Windows.Automation.Condition]::TrueCondition) | Where-Object { $_.Current.ControlType.ProgrammaticName -eq "ControlType.Text" } | ForEach-Object { $_.Current.Name }) -join " "
    if ($txt -like "*clientca.pem*") {
      $b = $w.FindFirst($S::Descendants, (New-Object System.Windows.Automation.PropertyCondition($ae::NameProperty, "Ignore for this session")))
      $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); "dismissed SSL warning after $i s"; break
    } else { "other warning: $txt"; break }
  }
}
