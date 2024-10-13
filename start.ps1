param (
    [string]$StartTemplate = "00000"
)

$startingTemplate = $StartTemplate
$templates = Get-ChildItem -Path ".\task_jsons" | 
Group-Object { $_.Name.Split('_')[0] } |
Where-Object { [int]$_.Name -ge [int]$startingTemplate } |
ForEach-Object { $_.Group | Sort-Object Name | Select-Object -First 1 } |
Sort-Object { [int]($_.Name.Split('_')[0]) }

foreach ($file in $templates) {
    $template = $file.Name
    
    Write-Host "Running template $template"
    
    $process = Start-Process -FilePath "python" -ArgumentList "main.py", "$template" -PassThru

    Read-Host "Press Enter to continue..."

    if ($process -and -not $process.HasExited) {
        $process.Kill()
        $process.WaitForExit()
    }
}
