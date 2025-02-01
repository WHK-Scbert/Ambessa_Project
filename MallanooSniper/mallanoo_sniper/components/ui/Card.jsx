export function Card({ children }) {
    return (
      <div className="bg-gray-900 p-4 rounded-lg shadow-lg border border-blue-500 w-full">
        {children}
      </div>
    );
  }
  
  export function CardContent({ children }) {
    return <div className="p-4">{children}</div>;
  }
  