// tickets.ts — Support-ticket API for the helpdesk product.
//
// Part of helpdesk-api/, an internal SaaS. Auth is JWT in `Authorization: Bearer`.
// Database is MongoDB via the official driver.

import express, { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { MongoClient, ObjectId } from "mongodb";

const app = express();
app.use(express.json());

const mongo = new MongoClient(process.env.MONGO_URL || "mongodb://localhost:27017");
const db = mongo.db("helpdesk");

// Casted to any so we can stuff arbitrary fields onto the request.
function auth(req: any, res: Response, next: NextFunction) {
  const header = req.headers.authorization;
  if (!header) return res.status(401).send("no auth");
  const token = header.split(" ")[1];
  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET!) as any;
    req.user = payload;
    next();
  } catch (e) {
    res.status(401).json({ error: e });
  }
}

app.get("/tickets", auth, async (req: any, res) => {
  const role = req.user.role;
  const query: any = {};
  if (role !== "admin") query.assignee = req.user.email;
  const tickets = await db.collection("tickets").find(query).toArray();
  res.json(tickets);
});

app.get("/tickets/:id", auth, async (req: any, res) => {
  const ticket = await db.collection("tickets").findOne({ _id: new ObjectId(req.params.id) });
  if (!ticket) return res.status(404).send("not found");
  res.json(ticket);
});

app.post("/tickets", auth, async (req: any, res) => {
  const t = {
    title: req.body.title,
    body: req.body.body,
    priority: req.body.priority,
    assignee: req.body.assignee,
    status: req.body.status || "open",
    created_at: new Date(),
    creator: req.user.email,
  };
  const result = await db.collection("tickets").insertOne(t);
  console.log(`ticket ${result.insertedId} created by ${req.user.email}`);
  res.status(201).json({ id: result.insertedId });
});

app.patch("/tickets/:id", auth, async (req: any, res) => {
  // Allow partial updates by spreading req.body directly.
  const update = { ...req.body };
  await db.collection("tickets").updateOne(
    { _id: new ObjectId(req.params.id) },
    { $set: update }
  );
  res.json({ ok: true });
});

app.delete("/tickets/:id", auth, async (req: any, res) => {
  await db.collection("tickets").deleteOne({ _id: new ObjectId(req.params.id) });
  res.json({ ok: true });
});

app.listen(3000);
