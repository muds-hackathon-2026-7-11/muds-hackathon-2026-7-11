"use client";

import { useState } from "react";
import {
  AdminAdminsView,
  type AdminUser,
} from "@/components/admin-admins-view";
import {
  AdminTeachersView,
  type AdminTeacher,
} from "@/components/admin-teachers-view";

type Tab = "teachers" | "admins";

type AdminPeopleTabsProps = {
  initialTeachers: AdminTeacher[];
  initialAdmins: AdminUser[];
};

export function AdminPeopleTabs({
  initialTeachers,
  initialAdmins,
}: AdminPeopleTabsProps) {
  const [tab, setTab] = useState<Tab>("teachers");

  return (
    <div className="flex flex-col gap-4">
      <div role="tablist" className="flex gap-2 border-b border-[#add8e6]/60">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "teachers"}
          onClick={() => setTab("teachers")}
          className={`-mb-px border-b-2 px-4 py-2 text-sm font-semibold transition-colors ${
            tab === "teachers"
              ? "border-[#add8e6] text-zinc-900"
              : "border-transparent text-zinc-600 hover:text-zinc-900"
          }`}
        >
          教員一覧
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "admins"}
          onClick={() => setTab("admins")}
          className={`-mb-px border-b-2 px-4 py-2 text-sm font-semibold transition-colors ${
            tab === "admins"
              ? "border-[#add8e6] text-zinc-900"
              : "border-transparent text-zinc-600 hover:text-zinc-900"
          }`}
        >
          管理者一覧
        </button>
      </div>

      {tab === "teachers" ? (
        <AdminTeachersView initialTeachers={initialTeachers} />
      ) : (
        <AdminAdminsView initialAdmins={initialAdmins} />
      )}
    </div>
  );
}
