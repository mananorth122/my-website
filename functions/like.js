export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const id = url.searchParams.get("id");
  const action = url.searchParams.get("action");

  if (!id) {
    return new Response(JSON.stringify({ error: "Missing id" }), { status: 400 });
  }

  const kv = env.LIKE_KV;

  // 【追加】id=all の場合は、KV内の全データをまとめて返す
  if (id === "all") {
    const allLikes = {};
    if (kv) {
      const list = await kv.list();
      for (const key of list.keys) {
        const val = await kv.get(key.name);
        allLikes[key.name] = val ? parseInt(val, 10) : 0;
      }
    }
    return new Response(JSON.stringify(allLikes), {
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
      }
    });
  }

  // --- 以下、これまでの単一記事用の処理 ---
  let count = 0;
  if (kv) {
    const current = await kv.get(id);
    count = current ? parseInt(current, 10) : 0;

    if (request.method === "POST") {
      if (action === "decrement") {
        count = Math.max(0, count - 1);
      } else {
        count += 1;
      }
      await kv.put(id, count.toString());
    }
  } else {
    if (request.method === "POST") {
      count = action === "decrement" ? 0 : 1;
    }
  }

  return new Response(JSON.stringify({ count }), {
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*"
    }
  });
}