export function Button({ children, onClick }) {
    return (
      <button
        onClick={onClick}
        className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-500 transition border border-blue-400 shadow-md"
      >
        {children}
      </button>
    );
  }
  