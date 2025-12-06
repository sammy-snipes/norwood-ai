<script setup>
defineProps({
  items: {
    type: Array,
    required: true
  },
  selectedId: {
    type: String,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  newButtonText: {
    type: String,
    default: '+ New'
  },
  emptyText: {
    type: String,
    default: 'No items yet'
  },
  alwaysShow: {
    type: Boolean,
    default: false
  }
})

defineEmits(['new', 'select', 'delete'])
</script>

<template>
  <aside :class="[
    'w-56 border-r border-gray-800 h-[calc(100vh-41px)] flex-col',
    alwaysShow ? 'flex' : 'hidden lg:flex'
  ]">
    <!-- New button -->
    <button
      @click="$emit('new')"
      class="m-2 py-1.5 bg-gray-800 hover:bg-gray-700 rounded text-[11px] text-gray-300 transition-colors"
    >
      {{ newButtonText }}
    </button>

    <h2 class="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-2 px-3">
      History
    </h2>

    <div v-if="loading" class="text-gray-500 text-[11px] px-3">
      Loading...
    </div>

    <div v-else-if="items.length === 0" class="text-gray-500 text-[11px] px-3">
      {{ emptyText }}
    </div>

    <div class="flex-1 overflow-y-auto">
      <div
        v-for="item in items"
        :key="item.id"
        @click="$emit('select', item)"
        :class="[
          'group px-3 py-1.5 transition-colors cursor-pointer flex items-center gap-2',
          selectedId === item.id
            ? 'bg-gray-700'
            : 'hover:bg-gray-800/50'
        ]"
      >
        <!-- Left slot for badge -->
        <slot name="badge" :item="item"></slot>

        <!-- Title -->
        <span class="text-[11px] text-gray-400 truncate flex-1">
          <slot name="title" :item="item">{{ item.title || 'Untitled' }}</slot>
        </span>

        <!-- Date (hidden on hover) -->
        <span class="text-[10px] text-gray-600 whitespace-nowrap group-hover:hidden">
          <slot name="date" :item="item"></slot>
        </span>

        <!-- Delete button (shown on hover) -->
        <button
          @click.stop="$emit('delete', item.id)"
          class="hidden group-hover:block text-[10px] text-gray-600 hover:text-red-400 transition-colors"
        >
          ✕
        </button>
      </div>
    </div>
  </aside>
</template>
