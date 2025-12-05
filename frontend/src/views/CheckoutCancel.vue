<script setup>
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white flex items-center justify-center px-4">
    <div class="max-w-md w-full text-center space-y-6">
      <div class="text-6xl mb-4">🤔</div>

      <h1 class="text-4xl font-black mb-4">Payment Cancelled</h1>

      <div class="p-6 bg-gray-800/50 rounded-lg border border-gray-700 space-y-4">
        <p class="text-gray-300 leading-relaxed">
          So you came all the way to the checkout page, stared at that $5 price tag,
          and decided... no. No, analyzing your hairline ad infinitum is not worth
          the cost of a mediocre latte.
        </p>

        <p class="text-gray-400 text-sm">
          We respect it. Perhaps you're saving up for a hair transplant instead.
          Or minoxidil. Or a really convincing hat.
        </p>

        <p class="text-gray-500 text-sm italic">
          Your free analysis is still waiting. For now.
        </p>
      </div>

      <div class="flex flex-col sm:flex-row gap-4 justify-center">
        <router-link
          to="/analyze"
          class="px-6 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium transition-colors"
        >
          Use My Free Analysis
        </router-link>

        <router-link
          to="/settings"
          class="px-6 py-3 bg-yellow-600 hover:bg-yellow-700 rounded-lg font-medium transition-colors"
        >
          Try Again ($5)
        </router-link>
      </div>
    </div>
  </div>
</template>
