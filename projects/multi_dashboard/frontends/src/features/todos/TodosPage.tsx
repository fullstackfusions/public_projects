import { FormEvent, useState } from "react";
import type { Todo } from "./types";
import { useTodos } from "./useTodos";

export function TodosPage() {
  const { todosQuery, createTodo, updateTodo, deleteTodo, toggleTodo } =
    useTodos();

  const todos = todosQuery.data ?? [];
  const loading = todosQuery.isLoading;
  const apiError = todosQuery.error?.message ?? null;

  const [editingTodo, setEditingTodo] = useState<Todo | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const inputClass =
    "rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm shadow-sm transition focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/40";
  const primaryButtonClass =
    "inline-flex items-center justify-center rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand/40 disabled:cursor-not-allowed disabled:opacity-70";
  const secondaryButtonClass =
    "inline-flex items-center justify-center rounded-xl bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-slate-300";
  const dangerButtonClass =
    "inline-flex items-center justify-center rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-500 focus:outline-none focus:ring-2 focus:ring-rose-300";

  function resetForm() {
    setEditingTodo(null);
    setNewTitle("");
    setNewDescription("");
    setFormError(null);
  }

  function handleEdit(todo: Todo) {
    setEditingTodo(todo);
    setNewTitle(todo.title);
    setNewDescription(todo.description || "");
    setFormError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    const title = newTitle.trim();
    if (!title) {
      setFormError("Title is required");
      return;
    }

    const description = newDescription.trim() || undefined;

    if (editingTodo) {
      await updateTodo.mutateAsync({
        id: editingTodo.id,
        payload: { title, description, completed: editingTodo.completed },
      });
    } else {
      await createTodo.mutateAsync({ title, description });
    }

    resetForm();
  }

  async function handleDelete(todo: Todo) {
    const confirmed = window.confirm(`Delete todo "${todo.title}"?`);
    if (confirmed) {
      await deleteTodo.mutateAsync(todo.id);
      if (editingTodo?.id === todo.id) {
        resetForm();
      }
    }
  }

  async function handleToggle(todo: Todo) {
    await toggleTodo.mutateAsync({ id: todo.id, completed: !todo.completed });
  }

  const activeTodos = todos.filter((t) => !t.completed);
  const completedTodos = todos.filter((t) => t.completed);

  return (
    <div className="flex flex-col gap-6 h-full">
      {(apiError || formError) && (
        <div className="rounded-xl border border-rose-200 bg-rose-100 px-4 py-3 text-sm text-rose-700 shadow-sm">
          {apiError || formError}
        </div>
      )}

      <div className="grid gap-7 xl:grid-cols-[minmax(320px,380px)_1fr] flex-1">
        <section className="space-y-6 rounded-2xl bg-white p-6 shadow-card">
          <h2 className="text-xl font-semibold text-slate-900">
            {editingTodo ? "Edit Todo" : "Create Todo"}
          </h2>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
              Title
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                className={inputClass}
                placeholder="What needs to be done?"
                required
              />
            </label>

            <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
              Description
              <textarea
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                className={`${inputClass} min-h-[80px] resize-y`}
                placeholder="Optional description"
                rows={3}
              />
            </label>

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                className={primaryButtonClass}
                disabled={loading}
              >
                {editingTodo ? "Update Todo" : "Add Todo"}
              </button>
              {editingTodo && (
                <button
                  type="button"
                  className={secondaryButtonClass}
                  onClick={resetForm}
                >
                  Cancel
                </button>
              )}
            </div>
          </form>
        </section>

        <section className="space-y-4 rounded-2xl bg-white p-6 shadow-card overflow-auto">
          <h2 className="text-xl font-semibold text-slate-900">Todo List</h2>

          {loading && todos.length === 0 ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : todos.length === 0 ? (
            <p className="text-sm text-slate-500">No todos yet. Create one!</p>
          ) : (
            <div className="space-y-6">
              {activeTodos.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                    Active ({activeTodos.length})
                  </h3>
                  <ul className="flex flex-col gap-3">
                    {activeTodos.map((todo) => (
                      <TodoItem
                        key={todo.id}
                        todo={todo}
                        onEdit={handleEdit}
                        onDelete={handleDelete}
                        onToggle={handleToggle}
                        secondaryButtonClass={secondaryButtonClass}
                        dangerButtonClass={dangerButtonClass}
                      />
                    ))}
                  </ul>
                </div>
              )}

              {completedTodos.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                    Completed ({completedTodos.length})
                  </h3>
                  <ul className="flex flex-col gap-3">
                    {completedTodos.map((todo) => (
                      <TodoItem
                        key={todo.id}
                        todo={todo}
                        onEdit={handleEdit}
                        onDelete={handleDelete}
                        onToggle={handleToggle}
                        secondaryButtonClass={secondaryButtonClass}
                        dangerButtonClass={dangerButtonClass}
                      />
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

interface TodoItemProps {
  todo: Todo;
  onEdit: (todo: Todo) => void;
  onDelete: (todo: Todo) => void;
  onToggle: (todo: Todo) => void;
  secondaryButtonClass: string;
  dangerButtonClass: string;
}

function TodoItem({
  todo,
  onEdit,
  onDelete,
  onToggle,
  secondaryButtonClass,
  dangerButtonClass,
}: TodoItemProps) {
  return (
    <li className="flex items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={todo.completed}
          onChange={() => onToggle(todo)}
          className="mt-1 h-5 w-5 rounded border-slate-300 text-brand focus:ring-brand/40"
        />
        <div className="space-y-1">
          <span
            className={`block text-base font-semibold ${
              todo.completed ? "text-slate-400 line-through" : "text-slate-900"
            }`}
          >
            {todo.title}
          </span>
          {todo.description && (
            <p
              className={`text-sm ${
                todo.completed ? "text-slate-400" : "text-slate-600"
              }`}
            >
              {todo.description}
            </p>
          )}
          <div className="text-xs text-slate-400">
            Created: {new Date(todo.created_at).toLocaleDateString()}
          </div>
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <button
          type="button"
          className={secondaryButtonClass}
          onClick={() => onEdit(todo)}
        >
          Edit
        </button>
        <button
          type="button"
          className={dangerButtonClass}
          onClick={() => onDelete(todo)}
        >
          Delete
        </button>
      </div>
    </li>
  );
}
