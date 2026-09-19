# Tui Observability

We need a TUI navigation observability, I was thinking about something like this:

```ts

interface keyPressed { 
  page: Page
  key: Key (also mouse clicked)
  created_at: Datetime
}

```

That feature should allow us to check which keys are pressed the most which is a hint of the annoyance of the app. 

The cool thing about this is that we could evolve this to a reconstruction of an user session, meaning we can reproduce bugs quickly