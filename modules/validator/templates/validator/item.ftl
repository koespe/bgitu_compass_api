<#if files?has_content>
    <#list files as file>
        <!--
           ИСПРАВЛЕНИЕ Z-INDEX:
           class="... hover:z-30 focus-within:z-50"

           Логика слоев теперь такая:
           1. Обычная строка: z-0 (или auto)
           2. Строка под мышкой (hover): z-30
           3. Строка с ОТКРЫТЫМ меню (focus-within): z-50

           Это гарантирует, что открытое меню (z-50) всегда будет ПОВЕРХ
           следующей строки, даже если вы наведете на неё мышь (z-30).
        -->
        <tr class="group relative border-b border-gray-100 hover:bg-gray-50 transition-colors duration-200 cursor-pointer hover:z-30 focus-within:z-50">

            <!-- Название -->
            <td class="px-5 py-4 sm:px-6">
                <!-- Ссылка на редактирование (фон) -->
                <a href="validator/edit?fileId=${file.fileId}" class="absolute inset-0 z-0 focus:outline-none"></a>

                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 flex items-center justify-center rounded-full bg-blue-50 text-blue-600">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
                    </div>
                    <div>
                        <span class="block font-medium text-gray-800 text-sm">
                            ${file.name}
                        </span>
                    </div>
                </div>
            </td>

            <!-- Дата -->
            <td class="px-5 py-4 sm:px-6">
                <p class="text-gray-500 text-sm">
                    ${file.formattedDateTime}
                </p>
            </td>

            <!-- Статус -->
            <td class="px-5 py-4 sm:px-6">
                <#if file.status == "SUCCESS">
                    <span class="inline-block rounded-full px-2.5 py-0.5 text-xs font-medium bg-green-50 text-green-700 border border-green-100">
                        Успешно
                    </span>
                <#elseif file.status == "PROCESSING">
                    <span class="inline-block rounded-full px-2.5 py-0.5 text-xs font-medium bg-yellow-50 text-yellow-700 border border-yellow-100 animate-pulse">
                        Обработка
                    </span>
                <#elseif file.status == "FAIL">
                    <span class="inline-block rounded-full px-2.5 py-0.5 text-xs font-medium bg-red-50 text-red-700 border border-red-100">
                        Ошибка
                    </span>
                <#else>
                    <span class="inline-block rounded-full px-2.5 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200">
                        Пусто
                    </span>
                </#if>
            </td>

            <!-- Действия -->
            <td class="px-5 py-4 sm:px-6 text-right overflow-visible">
                <!--
                    focus-within:opacity-100
                    Удерживает кнопки видимыми, пока открыто меню.
                -->
                <div class="relative z-10 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity duration-200 flex items-center justify-end gap-2">

                    <!-- Кнопка Открыть -->
                    <a target="_blank" rel="noopener noreferrer" href="validator/edit?fileId=${file.fileId}"
                       class="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-800 px-2 py-1">
                        Открыть
                    </a>

                    <!-- Выпадающее меню -->
                    <!-- Тег details открывается только по клику (стандарт HTML) -->
                    <details class="relative">
                        <summary class="list-none cursor-pointer p-1.5 rounded text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="12" cy="12" r="1"></circle>
                                <circle cx="12" cy="5" r="1"></circle>
                                <circle cx="12" cy="19" r="1"></circle>
                            </svg>
                        </summary>

                        <div class="absolute right-0 top-full z-50 w-40 rounded-lg border border-gray-200 bg-white shadow-lg py-1 text-left">
                            <a href="validator/files/download?fileId=${file.fileId}"
                               onclick="this.closest('details').removeAttribute('open')"
                               class="block w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-gray-900">
                                <div class="flex items-center gap-2">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                                    Скачать
                                </div>
                            </a>

                            <button hx-delete="validator/files/delete?fileId=${file.fileId}"
                                    hx-confirm="Вы действительно хотите удалить файл '${file.name}'? Это действие необратимо."
                                    hx-swap="none"
                                    onclick="this.closest('details').removeAttribute('open')"
                                    class="block w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50 hover:text-red-800 text-left">
                                <div class="flex items-center gap-2">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                                    Удалить
                                </div>
                            </button>
                        </div>
                    </details>

                </div>
            </td>
        </tr>
    </#list>
<#else>
    <td colspan="4" class="h-64 text-center">
        <div class="flex flex-col items-center justify-center gap-3">
            <svg class="h-10 w-10 text-gray-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
            </svg>
            <div class="flex flex-col">
                <span class="text-lg font-medium text-gray-600">Список файлов пуст</span>
                <span class="text-sm text-gray-400">Нажмите "Обновить", чтобы загрузить данные</span>
            </div>
        </div>
    </td>
</#if>