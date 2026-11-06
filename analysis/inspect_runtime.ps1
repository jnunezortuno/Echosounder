param([int]$ApplicationProcessId, [string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
public static class EchosounderWindowInspection {
  public delegate bool Callback(IntPtr hwnd, IntPtr parameter);
  [DllImport("user32.dll")] public static extern bool EnumWindows(Callback callback, IntPtr parameter);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hwnd, StringBuilder text, int length);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr hwnd, StringBuilder text, int length);
  public static List<IntPtr> Find(int target) {
    var found = new List<IntPtr>();
    EnumWindows((hwnd, parameter) => { uint pid; GetWindowThreadProcessId(hwnd, out pid); if(pid==target) found.Add(hwnd); return true; }, IntPtr.Zero);
    return found;
  }
}
'@
$windows = [EchosounderWindowInspection]::Find($ApplicationProcessId)
$rows = @(foreach ($handle in $windows) {
    $title = New-Object System.Text.StringBuilder 1024
    $className = New-Object System.Text.StringBuilder 256
    [void][EchosounderWindowInspection]::GetWindowText($handle,$title,1024)
    [void][EchosounderWindowInspection]::GetClassName($handle,$className,256)
    Write-Host ('Window ' + $handle + ' ' + $className + ' ' + $title)
    if ($title.ToString() -ne 'Echosounder v0.1') { continue }
    $element = [System.Windows.Automation.AutomationElement]::FromHandle($handle)
    $nodes = $element.FindAll([System.Windows.Automation.TreeScope]::Subtree,[System.Windows.Automation.Condition]::TrueCondition)
    foreach ($node in $nodes) {
        $value = $null
        $range = $null
        try { $value = $node.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value } catch {}
        try { $rv = $node.GetCurrentPattern([System.Windows.Automation.RangeValuePattern]::Pattern).Current; $range = @{Value=$rv.Value; Minimum=$rv.Minimum; Maximum=$rv.Maximum} } catch {}
        [pscustomobject]@{
            Name=$node.Current.Name
            AutomationId=$node.Current.AutomationId
            Class=$node.Current.ClassName
            Control=$node.Current.ControlType.ProgrammaticName
            Enabled=$node.Current.IsEnabled
            Handle=$node.Current.NativeWindowHandle
            Value=$value
            Range=$range
        }
    }
})
$rows | ConvertTo-Json -Depth 3 | Set-Content -Encoding UTF8 (Join-Path $OutputDirectory 'runtime_ui_main.json')
$rows | Format-Table -AutoSize
