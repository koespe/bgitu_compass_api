<#-- Определение цветов и иконок в зависимости от статуса -->
<#if file.status == "SUCCESS">
    <#assign bgClass = "bg-green-600">
    <#assign iconHtml>
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
    </#assign>
    <#assign text = "Успешно">
<#elseif file.status == "PROCESSING">
    <#assign bgClass = "bg-blue-600">
    <#assign iconHtml>
        <svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
    </#assign>
    <#assign text = "Обработка">
<#elseif file.status == "FAIL">
    <#assign bgClass = "bg-red-600">
    <#assign iconHtml>
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
    </#assign>
    <#assign text = "Ошибка">
<#else>
    <#assign bgClass = "bg-gray-700">
    <#assign iconHtml>
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
    </#assign>
    <#assign text = "Ожидание">
</#if>

<!-- Сам Toast -->
<div class="pointer-events-auto flex items-center gap-3 px-5 py-4 rounded-xl shadow-2xl ${bgClass} text-white transition-all duration-500 ease-in-out transform hover:scale-105">
    <div class="flex-shrink-0">
        ${iconHtml}
    </div>
    <div class="flex flex-col">
        <span class="text-sm font-bold leading-tight">${text}</span>
    </div>
</div>