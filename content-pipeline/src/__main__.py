from src.build import run_pipeline, generate_audio, write_outputs
import sys

def main() -> int:
    poems, errs = run_pipeline()
    if errs:
        print("\n".join(errs))
        return 1
    if "--audio" in sys.argv:
        n = None
        if "--limit" in sys.argv:
            n = int(sys.argv[sys.argv.index("--limit") + 1])
        generate_audio(poems, max_n=n)
    write_outputs(poems)
    print(f"OK: {len(poems)} 首已构建")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
