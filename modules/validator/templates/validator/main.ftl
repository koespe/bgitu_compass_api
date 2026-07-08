<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Панель управления</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js" integrity="sha384-/TgkGk7p307TH7EXJDuUlgG3Ce1UVolAOFopFekQkkXihi5u/6OCvVKyz1W+idaz" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/htmx-ext-sse@2.2.4" integrity="sha384-A986SAtodyH8eg8x8irJnYUk7i9inVQqYigD6qZ9evobksGNIXfeFvDwLSHcp31N" crossorigin="anonymous"></script>
    <link rel="icon" href="/static/logo/favico.ico" type="image/x-icon" nonce="">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        error: {
                            50: '#FEF2F2',
                            500: '#EF4444',
                            600: '#DC2626'
                        }
                    }
                }
            }
        }
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; }

        .custom-scrollbar::-webkit-scrollbar { width: 8px; height: 8px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background-color: #d1d5db; border-radius: 20px; border: 2px solid transparent; background-clip: content-box; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background-color: #9ca3af; }
    </style>
</head>
<body class="h-screen w-full flex overflow-hidden">

<aside class="flex flex-col w-64 bg-white border-r border-gray-200 shadow-sm">
    <div class="flex items-center justify-center h-16 border-b border-gray-200">
        <h1 class="text-xl font-bold text-gray-800">Панель управления</h1>
    </div>

    <nav class="flex-1 px-3 py-4 space-y-1">
        <button
            hx-get="/validator/content/schedule"
            hx-target="#main-content"
            hx-swap="innerHTML"
            class="tab-button w-full flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-all duration-200 text-white bg-blue-600 hover:bg-blue-700"
            onclick="setActiveTab(this)">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 mr-3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
            </svg>
            Расписание
        </button>

        <button
            hx-get="/validator/content/teachers"
            hx-target="#main-content"
            hx-swap="innerHTML"
            class="tab-button w-full flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-all duration-200 text-gray-700 hover:bg-gray-100"
            onclick="setActiveTab(this)">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 mr-3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" />
            </svg>
            Преподаватели
        </button>
    </nav>

    <div class="flex items-center justify-between p-4 border-t border-gray-200">
        <span class="text-sm font-medium text-gray-700 select-none">
            ${username}
        </span>

        <a href="/logout"
           class="group p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-all duration-200"
           title="Выйти">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-5 group-hover:scale-110 transition-transform">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
            </svg>
        </a>
    </div>
</aside>

<main id="main-content" hx-ext="sse" sse-connect="sse/validator/files" class="flex-1 flex flex-col overflow-hidden p-6">
    <div class="flex flex-col h-full w-full max-w-[1200px] mx-auto gap-6">
        <div id="errorReport" class="empty:hidden"></div>

        <div class="shrink-0 flex flex-wrap items-center justify-between gap-4 bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <h2 class="text-xl font-bold text-gray-800">Файлы расписания</h2>

            <div class="flex items-center gap-4">
                <div id="header-actions" class="flex items-center gap-3"></div>
            </div>
        </div>

        <div class="flex-1 min-h-0 flex flex-col rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
            <div class="flex-1 overflow-auto custom-scrollbar">
                <table class="w-full min-w-[900px] border-collapse">
                    <thead class="sticky top-0 z-10 bg-gray-50 shadow-sm">
                    <tr class="border-b border-gray-100">
                        <th class="px-5 py-3 text-left sm:px-6">
                            <p class="font-medium text-gray-500 text-sm">Название файла</p>
                        </th>
                        <th class="px-5 py-3 text-left sm:px-6">
                            <p class="font-medium text-gray-500 text-sm">Загружено</p>
                        </th>
                        <th class="px-5 py-3 text-left sm:px-6">
                            <p class="font-medium text-gray-500 text-sm">Статус</p>
                        </th>
                        <th class="px-5 py-3 text-left sm:px-6"></th>
                    </tr>
                    </thead>

                    <tbody sse-swap="updateFiles" class="bg-white divide-y divide-gray-100">
                    <tr>
                        <td colspan="4" class="px-5 py-8 text-center text-gray-500">
                            Подключение к потоку обновлений...
                        </td>
                    </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</main>

<script>
    function setActiveTab(button) {
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('text-white', 'bg-blue-600', 'hover:bg-blue-700');
            btn.classList.add('text-gray-700', 'hover:bg-gray-100');
        });
        button.classList.remove('text-gray-700', 'hover:bg-gray-100');
        button.classList.add('text-white', 'bg-blue-600', 'hover:bg-blue-700');
    }
</script>
</body>
</html>