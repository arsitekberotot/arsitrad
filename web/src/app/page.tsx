import { ArsitradWorkbench } from "@/components/arsitrad-workbench";

export default function Home() {
  return (
    <main className="mx-auto flex h-screen w-full max-w-[1600px] flex-col overflow-hidden px-4 py-4 sm:px-6 lg:px-8">
      <ArsitradWorkbench />
    </main>
  );
}
