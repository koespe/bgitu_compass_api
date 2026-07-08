<div id="header-actions" hx-swap-oob="true" class="flex items-center gap-3">

    <#assign disabledStyle = "bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed shadow-none">

    <a href="/schedule/rules"
            class="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 font-medium text-gray-700 hover:bg-gray-50 transition shadow-sm">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="stroke-gray-400">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
        </svg>
    </a>

    <#-- 1. КНОПКА СБРОСИТЬ -->
    <#if busy>
        <button disabled class="inline-flex items-center gap-2 rounded-lg border px-4 py-2 font-medium ${disabledStyle}">
            <svg class="stroke-gray-400" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 12"/></svg>
            Сбросить
        </button>
    <#else>
        <button hx-post="/schedule/refresh?uploadAll=true" hx-confirm="Вы уверены, что хотите сбросить состояние?" hx-swap="none"
                class="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-white px-4 py-2 font-medium text-red-600 hover:bg-red-50 transition shadow-sm">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 12"/></svg>
            Сбросить
        </button>
    </#if>

    <#-- 2. КНОПКА ОБНОВИТЬ -->
    <#if busy>
        <button disabled class="inline-flex items-center gap-2 rounded-lg border px-4 py-2 font-medium ${disabledStyle}">
            <svg class="stroke-gray-400" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
            Проверить обновления
        </button>
    <#else>
        <button hx-post="/schedule/refresh" hx-swap="none"
                class="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 font-medium text-gray-700 hover:bg-gray-50 transition shadow-sm">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
            Проверить обновления
        </button>
    </#if>

    <#-- 3. КНОПКА СКАЧАТЬ (Тег <a>) -->
    <#if busy || !canDownload>
        <!-- Для ссылки добавляем pointer-events-none, чтобы нельзя было кликнуть -->
        <a class="inline-flex items-center gap-2 rounded-lg border px-4 py-2 font-medium pointer-events-none ${disabledStyle}">
            <svg class="stroke-gray-400" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Скачать все
        </a>
    <#else>
        <a href="/validator/files/download"
           class="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 font-medium text-gray-700 hover:bg-gray-50 transition shadow-sm">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Скачать все
        </a>
    </#if>

    <#-- 4. КНОПКА ОТПРАВИТЬ (Синяя) -->
    <#if busy || !canSubmit>
        <button disabled class="inline-flex items-center gap-2 rounded-lg bg-blue-300 px-4 py-2 font-medium text-white/80 cursor-not-allowed shadow-none">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            Отправить
        </button>
    <#else>
        <button hx-post="/schedule/submit?keep=false" hx-confirm="Отправить данные на обработку?" hx-swap="none"
                class="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 transition shadow-md">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            Отправить
        </button>
    </#if>

</div>