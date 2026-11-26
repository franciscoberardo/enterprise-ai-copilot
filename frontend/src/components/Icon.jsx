const paths = {
    spark: "m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z",
    home: "m3 10 9-7 9 7v10H3V10Zm6 10v-7h6v7",
    users: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m18 0v-2a4 4 0 0 0-3-3.87M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm8-7.87a4 4 0 0 1 0 7.75",
    box: "m12 3 9 5v8l-9 5-9-5V8l9-5Zm0 9 9-4M12 12 3 8m9 4v9M7.5 5.5l9 5",
    orders: "M8 5H5v16h14V5h-3M8 3h8v4H8V3Zm0 9h8m-8 4h5",
    file: "M14 2H5v20h14V7l-5-5Zm0 0v6h5M8 12h8m-8 4h6",
    arrow: "M5 12h14m-6-6 6 6-6 6",
    search: "M21 21l-5-5M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z",
};

export default function Icon({ name, className = "size-5" }) {
    return (
        <svg
            className={className}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
        >
            <path d={paths[name] || paths.spark} />
        </svg>
    );
}
