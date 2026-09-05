export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const id = url.searchParams.get("id");

  if (!id) {
    return new Response(JSON.stringify({ error: "Missing id" }), { status: 400 });
  }

  // KVストレージが未設定の場合でも動作する簡易オンメモリ/レスポンス構造
  const kv = env.LIKE_KV;
  let count = 0;

  if (kv) {
    const current = await kv.get(id);
    count = current ? parseInt(current, 10) : 0;

    if (request.method === "POST") {
      count += 1;
      await kv.put(id, count.toString());
    }
  } else {
    // KV未連携時のテスト用レスポンス
    if (request.method === "POST") count = 1;
  }

  return new Response(JSON.stringify({ count }), {
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*"
    }
  });
}