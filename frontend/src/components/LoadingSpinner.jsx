import "./LoadingSpinner.css";

export default function LoadingSpinner({ message = "Loading..." }) {
  return (
    <div className="loading-spinner-container">
      <div className="spinner">
        <div className="spinner-ring"></div>
        <div className="spinner-ring"></div>
        <div className="spinner-ring"></div>
      </div>
      <p>{message}</p>
    </div>
  );
}
