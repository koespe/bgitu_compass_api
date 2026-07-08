<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Редактор файла</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="icon" href="/static/logo/favico.ico" type="image/x-icon" nonce="">
    <script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js" integrity="sha384-/TgkGk7p307TH7EXJDuUlgG3Ce1UVolAOFopFekQkkXihi5u/6OCvVKyz1W+idaz" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/htmx-ext-sse@2.2.4" integrity="sha384-A986SAtodyH8eg8x8irJnYUk7i9inVQqYigD6qZ9evobksGNIXfeFvDwLSHcp31N" crossorigin="anonymous"></script>
</head>
<body class="h-screen w-screen overflow-hidden bg-gray-900 relative">

<!-- IFRAME: Занимает все пространство -->
<!-- Важно: Google Sheets должен иметь права доступа, чтобы открыться в iframe -->
<iframe
        src="https://docs.google.com/spreadsheets/d/${fileId}/edit"
        class="w-full h-full border-none block"
        allow="autoplay">
</iframe>

<!--
    TOAST CONTAINER
    Расположен снизу справа (bottom-6 right-6).
    z-50 чтобы быть поверх iframe.

    hx-ext="sse": Включаем SSE
    sse-connect: Подключаемся к потоку конкретного файла
    sse-swap="StatusUpdate": Ждем именованное событие
-->
<div id="status-toast-container"
     class="fixed bottom-6 right-6 z-50 pointer-events-none"
     hx-ext="sse"
     sse-connect="/sse/validator/files?fileId=${fileId}"
     sse-swap="updateStatus">

    <!-- Начальное состояние (заглушка) -->
    <div class="pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg bg-gray-800 text-white animate-pulse">
        <div class="w-2 h-2 rounded-full bg-gray-400"></div>
        <span class="text-sm font-medium">Подключение к статусу...</span>
    </div>
</div>

</body>
</html>