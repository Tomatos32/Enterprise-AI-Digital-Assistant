import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import net from 'net';

function isPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => resolve(false));
    server.once('listening', () => {
      server.close(() => resolve(true));
    });
    server.listen(port, '127.0.0.1');
  });
}

async function resolveSafePort(candidatePorts) {
  for (const p of candidatePorts) {
    if (await isPortAvailable(p)) {
      return p;
    }
  }
  return 30010;
}

export default defineConfig(async () => {
  // Probes ports to bypass Windows Hyper-V / WinNAT dynamic exclusion ranges (EACCES)
  // Priority: 3001 (user preferred) -> 3000 -> 30010 / 30001 (immune to kernel ranges) -> 8081
  const port = await resolveSafePort([3001, 3000, 30010, 30001, 8081, 5173]);

  return {
    plugins: [vue()],
    server: {
      port,
      strictPort: false,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          ws: true,
        },
      },
    },
  };
});
