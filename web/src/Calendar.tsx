import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import luxonPlugin from "@fullcalendar/luxon3";
import type { Candidate, Plan } from "./types";

export default function Calendar({
  plan,
  candidate,
}: {
  plan: Plan;
  candidate: Candidate;
}) {
  return (
    <FullCalendar
      plugins={[timeGridPlugin, luxonPlugin]}
      initialView="timeGridWeek"
      locale="en"
      timeZone={plan.preferences.timezone}
      initialDate={candidate.events[0]?.start || plan.preferences.deadline}
      headerToolbar={{ left: "prev,next", center: "title", right: "" }}
      height="auto"
      allDaySlot={false}
      slotMinTime={plan.preferences.work_start}
      slotMaxTime={plan.preferences.work_end}
      nowIndicator
      weekends={plan.preferences.workdays.some((d) => d > 4)}
      events={[
        ...plan.busy_blocks.map((e, i) => ({
          ...e,
          id: `busy-${i}`,
          title: "Busy",
          backgroundColor: "#e0e4df",
          borderColor: "#e0e4df",
          textColor: "#58645b",
        })),
        ...candidate.events.map((e) => ({
          ...e,
          title: e.name,
          backgroundColor: "#d5eade",
          borderColor: "#9ecbb3",
          textColor: "#1c4938",
        })),
      ]}
    />
  );
}
