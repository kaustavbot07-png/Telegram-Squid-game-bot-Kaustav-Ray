export default {
  async fetch(request, env, ctx) {
    return new Response('Worker is running. Use the scheduled trigger to ping the bot.');
  },
  async scheduled(event, env, ctx) {
    const url = env.BOT_URL;
    if (!url) {
      console.log('BOT_URL environment variable is not set. Please set it in wrangler.toml or the Cloudflare dashboard.');
      return;
    }

    try {
      const response = await fetch(url);
      console.log(`Pinged ${url}: ${response.status}`);
    } catch (error) {
      console.error(`Error pinging ${url}: ${error}`);
    }
  },
};
