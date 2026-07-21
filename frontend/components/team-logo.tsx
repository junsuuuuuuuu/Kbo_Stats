import Image from "next/image";

const TEAM_LOGO_PATHS: Readonly<Record<string, string>> = {
  HH: "/team-logos/HH.png",
  HT: "/team-logos/HT.png",
  KT: "/team-logos/KT.png",
  LG: "/team-logos/LG.png",
  LT: "/team-logos/LT.png",
  NC: "/team-logos/NC.png",
  OB: "/team-logos/OB.png",
  SK: "/team-logos/SK.png",
  SS: "/team-logos/SS.png",
  WO: "/team-logos/WO.png",
};

interface TeamLogoProps {
  teamCode: string;
  teamName: string;
  size?: "default" | "large";
}

/** 모든 구단 화면이 동일한 공식 엠블럼과 대체 텍스트를 사용하게 한다. */
export function TeamLogo({ teamCode, teamName, size = "default" }: TeamLogoProps) {
  const normalizedCode = teamCode.toUpperCase();
  const source = TEAM_LOGO_PATHS[normalizedCode];
  const className = `team-logo${size === "large" ? " large" : ""}`;

  if (!source) {
    return <span className={`${className} fallback`}>{teamName.slice(0, 2)}</span>;
  }

  return (
    <span className={className}>
      <Image
        alt={`${teamName} 공식 엠블럼`}
        height={41}
        priority={size === "large"}
        src={source}
        width={64}
      />
    </span>
  );
}
