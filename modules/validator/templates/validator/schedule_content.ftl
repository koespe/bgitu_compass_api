<div class="flex flex-col h-full w-full max-w-[1200px] mx-auto gap-6" hx-ext="sse" sse-connect="/sse/validator/files">
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
