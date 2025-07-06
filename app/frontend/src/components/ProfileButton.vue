<template>
  <button class="profile-button">
    <span>WGP</span>
  </button>
</template>

<script setup lang="ts">
// Add any logic here for navigation to profile/auth
</script>

<style scoped>
.profile-button {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 999;
  background: rgb(237, 161, 9);
  border: none;

  /* make it a perfect circle: */
  width: 50px;
  height: 50px;
  padding: 0;               /* no extra padding */
  border-radius: 50%;

  /* center “WGP” inside: */
  display: flex;
  align-items: center;
  justify-content: center;

  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

.profile-button:hover {
  background: #f0f0f0;
}
</style>