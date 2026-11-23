"""Build branded, bundled Android/Windows applications from the local assets.

Only a publishable Supabase URL/key is allowed into the client configuration.
Signing keys are external to the repository and used by the Android signer.
"""
import argparse
import base64
import hashlib
import json
import csv
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mobile" / "windows"))
from PIL import Image, ImageDraw


def make_icon(destination):
    image=Image.new("RGBA",(512,512))
    draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((0,0,511,511),radius=126,fill="#193b55")
    for x,y,color in ((104,104,"#80e1c9"),(280,104,"#e5a3ee"),(104,280,"#f4bb7a"),(280,280,"#afb7ff")):
        draw.rounded_rectangle((x,y,x+128,y+128),radius=35,outline=color,width=25)
    image.save(destination,sizes=[(n,n) for n in (16,24,32,48,64,128,256)])


def run(*args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def validate_public(url, key):
    if not url and not key:
        return ""
    match = re.fullmatch(r"https://([a-z0-9]+\.supabase\.co)", url)
    if not match:
        raise ValueError("Expected a Supabase HTTPS project URL.")
    if not key.startswith("sb_publishable_"):
        # Legacy JWT must explicitly have the anon role, never service_role.
        try:
            payload = key.split(".")[1]
            role = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["role"]
        except Exception:
            raise ValueError("Use a public publishable/anon key only.") from None
        if role != "anon":
            raise ValueError("Use a public publishable/anon key only.")
    return match.group(1)


def stage(work, args):
    web = work / "web"
    shutil.copytree(ROOT / "standalone" / "web", web)
    shutil.copytree(args.assets, web / "assets")
    host = validate_public(args.url, args.key)
    (web / "config.js").write_text("window.MP_CONFIG=" + json.dumps({"url": args.url, "key": args.key}) + ";\n")
    catalogs = {"en": {}}
    for source in (ROOT / "translations").glob("*.json"):
        catalogs[source.stem] = json.loads(source.read_text(encoding="utf-8"))
    with (ROOT / "standalone" / "workspace-locales.tsv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            if not row.get("key") or None in row or any(not row.get(code) for code in catalogs if code != "en"):
                raise ValueError("Invalid common localization row")
            for code in catalogs:
                if code != "en": catalogs[code][row["key"]] = row[code]
    with (ROOT / "standalone" / "workspace-hi.tsv").open(encoding="utf-8", newline="") as stream:
        for original,translated in csv.reader(stream, delimiter="\t"):
            catalogs["hi"][original] = translated
    with (ROOT / "standalone" / "workspace-de.tsv").open(encoding="utf-8", newline="") as stream:
        for original,translated in csv.reader(stream, delimiter="\t"):
            catalogs["de"][original] = translated
    for filename in ("workspace-ui-extra.tsv","workspace-ui-indic.tsv"):
        with (ROOT / "standalone" / filename).open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream, delimiter="\t"):
                if not row.get("key") or None in row:
                    raise ValueError("Invalid extra localization row")
                for code,translated in row.items():
                    if code in catalogs and translated: catalogs[code][row["key"]]=translated
    # Every locale receives the broader module vocabulary. Existing Hindi /
    # German translations remain available when a row omits those two cells.
    with (ROOT / "standalone" / "workspace-all-languages.psv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="|"):
            if not row.get("key") or None in row or any(not row.get(code) for code in catalogs if code not in ("en", "hi", "de")):
                raise ValueError("Invalid multilingual localization row: " + str(row.get("key")))
            for code,translated in row.items():
                if code in catalogs and translated:
                    catalogs[code][row["key"]]=translated
    # Compare case-insensitively, exactly as the runtime translator does.
    # Prevent future changes from expanding only a subset of the languages.
    expected=set().union(*(set(k.casefold() for k in d) for code,d in catalogs.items() if code!="en"))
    for code,d in catalogs.items():
        if code=="en":continue
        missing=expected-{k.casefold() for k,v in d.items() if v.strip()}
        if missing:raise ValueError(f"Incomplete localization ({code}): {', '.join(sorted(missing))}")
    (web / "locale-data.js").write_text("window.MPI18nCatalogs="+json.dumps(catalogs,ensure_ascii=False,separators=(",",":"))+";\n",encoding="utf-8")
    vendor = web / "vendor"
    vendor.mkdir()
    for name in ("pdf.min.mjs", "pdf.worker.min.mjs"):
        shutil.copy(args.pdfjs / "build" / name, vendor / name)
    shutil.copy(args.pdfjs / "LICENSE", vendor / "PDFJS-LICENSE.txt")
    return web, host


def android(work, web, host, args):
    tools = args.build_tools.resolve()
    jar = args.android_jar.resolve()
    build = work / "android"
    build.mkdir()
    for name in ["classes", "generated", "dex"]:
        (build/name).mkdir()
    shutil.copytree(ROOT/"mobile/android/app/src/main/res", build/"res")
    (build/"res/drawable/medical_box.xml").write_text('<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="108dp" android:height="108dp" android:viewportWidth="108" android:viewportHeight="108"><path android:fillColor="#193B55" android:pathData="M0,0H108V108H0Z"/><path android:fillColor="#80E1C9" android:pathData="M30,30H50V50H30Z"/><path android:fillColor="#E5A3EE" android:pathData="M58,30H78V50H58Z"/><path android:fillColor="#F4BB7A" android:pathData="M30,58H50V78H30Z"/><path android:fillColor="#AFB7FF" android:pathData="M58,58H78V78H58Z"/></vector>')
    (build/"res/values/standalone.xml").write_text('<resources><string name="mp_project_host" translatable="false">'+host+'</string></resources>')
    shutil.copytree(web, build/"assets/web")
    run(tools/"aapt2","compile","--dir",build/"res","-o",build/"resources.zip")
    run(tools/"aapt2","link","-o",build/"unsigned.apk","-I",jar,
        "--manifest",ROOT/"standalone/android/AndroidManifest.xml","--java",build/"generated",
        "--min-sdk-version","26","--target-sdk-version","35","--version-code","5",
        "--version-name","1.1.3","-A",build/"assets",build/"resources.zip")
    sources=list((build/"generated").rglob("*.java"))+[ROOT/"standalone/android/StandaloneActivity.java"]
    run("java","com.sun.tools.javac.Main","-encoding","UTF-8","-source","8","-target","8",
        "-Xlint:-options","-bootclasspath",os.pathsep.join([str(tools/"core-lambda-stubs.jar"),str(jar)]),
        "-d",build/"classes",*sources)
    run("java","-cp",tools/"lib/d8.jar","com.android.tools.r8.D8","--release","--lib",jar,
        "--min-api","26","--output",build/"dex",*sorted((build/"classes").rglob("*.class")))
    with zipfile.ZipFile(build/"unsigned.apk","a",compression=zipfile.ZIP_DEFLATED) as apk:
        for dex in (build/"dex").glob("*.dex"):apk.write(dex,dex.name)
    run(tools/"zipalign","-f","-P","16","4",build/"unsigned.apk",build/"aligned.apk")
    signing=args.signing_dir.resolve()
    key=signing/"medpredict.jks"
    if not key.is_file() or not (signing/"signing-password.txt").is_file():
        raise RuntimeError("Existing private Android signing files required.")
    env=os.environ.copy()
    env["MEDPREDICT_SIGNING_PASSWORD"]=(signing/"signing-password.txt").read_text().strip()
    output=args.out/"Aroham-AI.apk"
    run("java","-jar",tools/"lib/apksigner.jar","sign","--ks",key,
        "--ks-key-alias","medpredict","--ks-pass","env:MEDPREDICT_SIGNING_PASSWORD",
        "--key-pass","env:MEDPREDICT_SIGNING_PASSWORD","--min-sdk-version","26",
        "--v1-signing-enabled","true","--v2-signing-enabled","true","--out",output,build/"aligned.apk",env=env)
    run("java","-jar",tools/"lib/apksigner.jar","verify","--verbose","--print-certs",output)
    run(tools/"zipalign","-c","-P","16","4",output)
    run(tools/"aapt2","dump","badging",output)
    print(output,hashlib.sha256(output.read_bytes()).hexdigest())


def windows(work, web,args):
    zig=args.zig.resolve()
    build=work/"windows"
    build.mkdir()
    shutil.copy(ROOT/"standalone/windows/MedPredict.c",build/"MedPredict.c")
    shutil.copy(ROOT/"mobile/windows/MedPredict.manifest",build/"MedPredict.manifest")
    make_icon(build/"MedPredict.ico")
    rc=(ROOT/"mobile/windows/MedPredict.rc").read_text().replace("1,2,0,0","1,1,3,0").replace("1.2.0","1.1.3").replace('MedPredict.exe','Aroham-AI.exe').replace('MedPredict\\0','Aroham AI\\0')
    mime={".html":"text/html; charset=utf-8",".css":"text/css; charset=utf-8",".js":"text/javascript; charset=utf-8",".mjs":"text/javascript; charset=utf-8",".json":"application/json; charset=utf-8",".svg":"image/svg+xml",".webp":"image/webp",".txt":"text/plain; charset=utf-8"}
    lines=["static const struct {const char *path; const char *mime; int id;} bundle[] = {"]
    for i,file in enumerate(sorted(web.rglob("*")),100):
        if not file.is_file():continue
        relative=file.relative_to(web).as_posix()
        rc+='\n'+str(i)+' RCDATA "'+str(file).replace("\\","/")+'"\n'
        lines.append('  {"/'+relative+'","'+mime.get(file.suffix,"application/octet-stream")+'",'+str(i)+'},')
    lines.append("};")
    (build/"bundle.h").write_text("\n".join(lines))
    (build/"MedPredict.rc").write_text(rc)
    run(zig,"rc","/fo","MedPredict.res","MedPredict.rc",cwd=build)
    output=args.out/"Aroham-AI.exe"
    run(zig,"cc","-target","x86_64-windows-gnu","-O2","-s","-municode","-Wl,--subsystem,windows","MedPredict.c","MedPredict.res","-lws2_32","-lshell32","-luser32","-lgdi32","-o",output,cwd=build)
    shutil.copy(build/"MedPredict.ico",args.out/"Aroham-AI.ico")
    print(output,hashlib.sha256(output.read_bytes()).hexdigest())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--assets",type=Path,required=True)
    p.add_argument("--pdfjs",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--android-jar",type=Path,required=True)
    p.add_argument("--build-tools",type=Path,required=True)
    p.add_argument("--signing-dir",type=Path,required=True)
    p.add_argument("--zig",type=Path,required=True)
    p.add_argument("--url",default="")
    p.add_argument("--key",default="")
    p.add_argument("--stage-only",action="store_true")
    args=p.parse_args()
    args.out=args.out.resolve()
    args.out.mkdir(parents=True,exist_ok=True)
    if args.stage_only:
        stage(args.out,args)
        return
    with TemporaryDirectory(prefix="medpredict-standalone-") as directory:
        work=Path(directory)
        web,host=stage(work,args)
        android(work,web,host,args)
        windows(work,web,args)

if __name__=="__main__":main()
