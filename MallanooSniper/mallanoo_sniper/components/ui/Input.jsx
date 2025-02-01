export function Input({ value, onChange, placeholder }) {
    return (
      <input
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="bg-gray-800 text-white border border-blue-500 p-2 rounded-md w-full focus:outline-none focus:ring-2 focus:ring-blue-400"
      />
    );
  }
  