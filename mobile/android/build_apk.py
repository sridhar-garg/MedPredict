#!/usr/bin/env python3
"""Build the small Android host using official Android SDK tools and a JDK.

No Gradle, Python backend, model files or third-party Android libraries are
packaged in the APK. Keep the signing directory private and reuse it for updates.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import zipfile
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from release_url import release_url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--android-jar', required=True, type=Path)
    parser.add_argument('--build-tools', required=True, type=Path)
    parser.add_argument('--signing-dir', type=Path, default=ROOT/'signing')
    parser.add_argument('--out', type=Path, default=ROOT/'build'/'MedPredict-Android.apk')
    parser.add_argument('--app-url', required=True, type=release_url, help='Verified independent HTTPS deployment')
    args = parser.parse_args()
    tools = args.build_tools.resolve()
    android = args.android_jar.resolve()
    build = ROOT/'build'
    build.mkdir(exist_ok=True)
    for name in ['classes', 'generated', 'dex', 'res']:
        directory = build/name
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir()

    def run(*command, **kwargs):
        subprocess.run([str(x) for x in command], check=True, cwd=ROOT, **kwargs)

    source = ROOT/'app'/'src'/'main'
    shutil.copytree(source/'res', build/'res', dirs_exist_ok=True)
    statements = json.dumps([{"relation": ["delegate_permission/common.handle_all_urls"],
                             "target": {"namespace": "web", "site": args.app_url.rstrip("/")}}], separators=(",", ":"))
    statements = escape(statements.replace('"', '\\"'))
    (build/'res'/'values'/'deployment.xml').write_text(
        '<resources><string name="app_url" translatable="false">' + escape(args.app_url) + '</string>'
        '<string name="asset_statements" translatable="false">' + statements + '</string></resources>', encoding='utf-8')
    run(tools/'aapt2', 'compile', '--dir', build/'res', '-o', build/'resources.zip')
    run(tools/'aapt2', 'link', '-o', build/'unsigned.apk', '-I', android,
        '--manifest', source/'AndroidManifest.xml', '--java', build/'generated',
        '--min-sdk-version', '26', '--target-sdk-version', '35',
        '--version-code', '3', '--version-name', '1.2.0', build/'resources.zip')
    for file in sorted((source/'aidl').rglob('*.aidl')):
        run(tools/'aidl', '--lang=java', '--min_sdk_version=26', '-p' + str(android.parent/'framework.aidl'),
            '-I' + str(source/'aidl'), '-o' + str(build/'generated'), file)
    java_sources = sorted((source/'java').rglob('*.java')) + sorted((build/'generated').rglob('*.java'))
    bootclasspath = os.pathsep.join([str(tools/'core-lambda-stubs.jar'), str(android)])
    run('java', 'com.sun.tools.javac.Main', '-encoding', 'UTF-8', '-source', '8', '-target', '8',
        '-Xlint:-options', '-bootclasspath', bootclasspath, '-d', build/'classes', *java_sources)
    classes = sorted((build/'classes').rglob('*.class'))
    run('java', '-cp', tools/'lib'/'d8.jar', 'com.android.tools.r8.D8',
        '--release', '--lib', android, '--min-api', '26', '--output', build/'dex', *classes)
    with zipfile.ZipFile(build/'unsigned.apk', 'a', compression=zipfile.ZIP_DEFLATED) as apk:
        for dex in sorted((build/'dex').glob('*.dex')):
            apk.write(dex, dex.name)
    run(tools/'zipalign', '-f', '-P', '16', '4', build/'unsigned.apk', build/'aligned.apk')

    signing = args.signing_dir.resolve()
    signing.mkdir(mode=0o700, parents=True, exist_ok=True)
    key, password = signing/'medpredict.jks', signing/'signing-password.txt'
    if key.exists() != password.exists():
        raise RuntimeError('Both the original signing key and password are needed for an update.')
    if not password.exists():
        password.write_text(secrets.token_urlsafe(40))
        password.chmod(0o600)
    env = os.environ.copy()
    env['MEDPREDICT_SIGNING_PASSWORD'] = password.read_text().strip()
    if not key.exists():
        run('keytool', '-genkeypair', '-keystore', key, '-alias', 'medpredict',
            '-storepass:env', 'MEDPREDICT_SIGNING_PASSWORD', '-keypass:env', 'MEDPREDICT_SIGNING_PASSWORD',
            '-keyalg', 'RSA', '-keysize', '3072', '-validity', '10000',
            '-dname', 'CN=MedPredict Local Distribution, OU=MedPredict', env=env)
        key.chmod(0o600)
    output = args.out.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    run('java', '-jar', tools/'lib'/'apksigner.jar', 'sign', '--ks', key,
        '--ks-key-alias', 'medpredict', '--ks-pass', 'env:MEDPREDICT_SIGNING_PASSWORD',
        '--key-pass', 'env:MEDPREDICT_SIGNING_PASSWORD', '--min-sdk-version', '26',
        '--v1-signing-enabled', 'true', '--v2-signing-enabled', 'true',
        '--out', output, build/'aligned.apk', env=env)
    run('java', '-jar', tools/'lib'/'apksigner.jar', 'verify', '--verbose', '--print-certs', output)
    run(tools/'zipalign', '-c', '-P', '16', '4', output)
    run(tools/'aapt2', 'dump', 'badging', output)
    print('APK:', output)
    print('SHA-256:', hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
