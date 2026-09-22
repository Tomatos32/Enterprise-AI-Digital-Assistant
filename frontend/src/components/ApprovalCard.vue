<template>
  <ApprovalCard
    :approval="approvalData || approval"
    :approvalData="approvalData || approval"
    @decision="handleDecision"
    @action="handleAction"
  />
</template>

<script setup>
import ApprovalCard from './chat/ApprovalCard.vue';

const props = defineProps({
  approvalData: {
    type: Object,
    default: null
  },
  approval: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['action', 'decision']);

const handleDecision = (id, action, comment) => {
  emit('decision', id, action, comment);
  emit('action', id, action, comment);
};

const handleAction = (id, action, comment) => {
  emit('action', id, action, comment);
  emit('decision', id, action, comment);
};
</script>
