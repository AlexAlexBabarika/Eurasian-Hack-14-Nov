import OpenAI from "openai";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

export async function POST(req: Request) {
  const { user, message } = await req.json();

  console.log("chat request from", user.email, message);

  const completion = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [
      { role: "system", content: "You are Notely, a helpful note-taking assistant." },
      { role: "user", content: message },
    ],
    user: user.email,
  });

  return Response.json({ reply: completion.choices[0].message.content });
}
