const paths = {
  arrow: "M5 12h14m-6-6 6 6-6 6",
  chevron: "m9 5 7 7-7 7",
  check: "m5 12 4 4L19 6",
  plus: "M12 5v14M5 12h14",
  book: "M4 4h7l1 2 1-2h7v15h-7l-1 2-1-2H4zM12 6v15",
  course: "M5 4h14v16H5zM8 8h8M8 12h5M8 16h8",
  leave: "M10 4H5v16h5M10 12h11m-4-4 4 4-4 4",
  other: "M4 5h16v12H9l-5 4zM8 9h8M8 13h5",
  close: "m6 6 12 12M18 6 6 18",
  user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8M4 21v-2a8 8 0 0 1 16 0v2",
  clock: "M12 8v4l3 2M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18",
};
export default function Icon({ name, size = 20, ...props }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      <path d={paths[name] || paths.other} />
    </svg>
  );
}
