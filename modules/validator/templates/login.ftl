<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Вход в систему</title>
    <link rel="icon" href="/static/logo/favico.ico" type="image/x-icon" nonce="">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center p-4">
<div class="w-full max-w-[400px] bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">

    <div class="p-6 sm:p-8">
        <div class="mb-6 text-center">
            <h2 class="text-2xl font-bold text-gray-800">Добро пожаловать</h2>
            <p class="text-gray-500 mt-2 text-sm">Введите данные для входа</p>
        </div>

        <form action="/login" method="post" class="space-y-5">
            <div>
                <label class="mb-2.5 block font-medium text-gray-700 text-sm">
                    Логин
                </label>
                <div class="relative">
                    <input type="text"
                           name="username"
                           autocomplete="username"
                           placeholder="Введите логин"
                           required
                           class="w-full rounded-lg border border-gray-300 bg-transparent py-3 px-5 text-gray-800 outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600 transition disabled:cursor-default disabled:bg-gray-50">

                    <span class="absolute right-4 top-4">
                            <svg class="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                            </svg>
                        </span>
                </div>
            </div>

            <div>
                <label class="mb-2.5 block font-medium text-gray-700 text-sm">
                    Пароль
                </label>
                <div class="relative">
                    <input type="password"
                           name="password"
                           autocomplete="current-password"
                           placeholder="Введите пароль"
                           required
                           class="w-full rounded-lg border border-gray-300 bg-transparent py-3 px-5 text-gray-800 outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600 transition disabled:cursor-default disabled:bg-gray-50">

                    <span class="absolute right-4 top-4">
                            <svg class="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                            </svg>
                        </span>
                </div>
            </div>

            <#if error??>
                <div class="p-3 rounded-lg bg-red-50 border border-red-100 text-red-600 text-sm flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    ${error}
                </div>
            </#if>

            <button type="submit"
                    class="w-full cursor-pointer rounded-lg border border-blue-600 bg-blue-600 p-3 text-white transition hover:bg-blue-700 font-medium">
                Войти
            </button>
        </form>
    </div>
</div>

</body>
</html>