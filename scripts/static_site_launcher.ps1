param([int]$Port = 8765, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$siteRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'site'))
if (-not (Test-Path -LiteralPath (Join-Path $siteRoot 'index.html'))) { throw 'Missing site/index.html. Extract the entire ZIP first.' }
$listener = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, $Port)
try { $listener.Start() } catch {
    $listener = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, 0)
    $listener.Start()
}
$actualPort = $listener.LocalEndpoint.Port
$url = "http://127.0.0.1:$actualPort/"
Write-Output "KPL Insight local snapshot: $url"
Write-Output 'Keep this window open while browsing. Close it to stop. No administrator rights or Python required.'
if (-not $NoBrowser) { Start-Process $url }
$types = @{ '.html'='text/html; charset=utf-8'; '.js'='application/javascript; charset=utf-8'; '.json'='application/json; charset=utf-8'; '.css'='text/css; charset=utf-8'; '.png'='image/png'; '.jpg'='image/jpeg'; '.jpeg'='image/jpeg'; '.svg'='image/svg+xml'; '.woff2'='font/woff2'; '.ico'='image/x-icon'; '.webp'='image/webp' }
try {
    while ($true) {
        $client = $listener.AcceptTcpClient()
        try {
            $client.ReceiveTimeout = 4000
            $stream = $client.GetStream()
            $reader = New-Object IO.StreamReader($stream, [Text.Encoding]::ASCII, $false, 4096, $true)
            $request = $reader.ReadLine()
            if (-not $request) { continue }
            $parts = $request.Split(' ')
            $method = $parts[0]
            $target = ($parts[1] -split '\?',2)[0]
            for ($n=0; $n -lt 100; $n++) { $header = $reader.ReadLine(); if (-not $header) { break } }
            $decoded = [Uri]::UnescapeDataString($target)
            $relative = $decoded.TrimStart('/').Replace('/', [IO.Path]::DirectorySeparatorChar)
            if (-not $relative) { $relative = 'index.html' }
            $path = [IO.Path]::GetFullPath((Join-Path $siteRoot $relative))
            $inside = $path.StartsWith($siteRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)
            $status = '200 OK'
            if ($method -ne 'GET' -and $method -ne 'HEAD') { $status='405 Method Not Allowed' }
            elseif (-not $inside) { $status='403 Forbidden' }
            elseif (-not [IO.File]::Exists($path)) { $status='404 Not Found' }
            if ($status -eq '200 OK') {
                $body = [IO.File]::ReadAllBytes($path)
                $type = $types[[IO.Path]::GetExtension($path).ToLowerInvariant()]
                if (-not $type) { $type='application/octet-stream' }
            } else {
                $body = [Text.Encoding]::UTF8.GetBytes($status)
                $type = 'text/plain; charset=utf-8'
            }
            $response = "HTTP/1.1 $status`r`nContent-Type: $type`r`nContent-Length: $($body.Length)`r`nConnection: close`r`nCache-Control: no-cache`r`nX-Content-Type-Options: nosniff`r`n`r`n"
            $bytes = [Text.Encoding]::ASCII.GetBytes($response)
            $stream.Write($bytes, 0, $bytes.Length)
            if ($method -ne 'HEAD') { $stream.Write($body, 0, $body.Length) }
            $stream.Flush()
        } catch { Write-Verbose $_ } finally { $client.Close() }
    }
} finally { $listener.Stop() }
