#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#define COBJMACROS
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <shlobj.h>
#include <shobjidl.h>
#include <strsafe.h>
#include <wchar.h>
#include <stdlib.h>

#define CAP 2048
static const wchar_t *app_url =
    L"https://medpredictgit-gwv3verd6e57qygyixu5zs.streamlit.app/?embed=true";
static const wchar_t *uninstall_key =
    L"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\MedPredict";

typedef struct {
    wchar_t program_dir[CAP], directory[CAP], executable[CAP];
    wchar_t desktop_link[CAP], start_link[CAP];
} AppPaths;

static BOOL join(wchar_t *out, const wchar_t *base, const wchar_t *suffix) {
    return SUCCEEDED(StringCchPrintfW(out, CAP, L"%ls\\%ls", base, suffix));
}

static BOOL known_folder(const KNOWNFOLDERID *id, wchar_t *out) {
    PWSTR path = NULL;
    HRESULT hr = SHGetKnownFolderPath(id, 0, NULL, &path);
    if (FAILED(hr)) return FALSE;
    hr = StringCchCopyW(out, CAP, path);
    CoTaskMemFree(path);
    return SUCCEEDED(hr);
}

static BOOL app_paths(AppPaths *paths) {
    wchar_t base[CAP], desktop[CAP], programs[CAP];
    return known_folder(&FOLDERID_LocalAppData, base) &&
           known_folder(&FOLDERID_Desktop, desktop) &&
           known_folder(&FOLDERID_Programs, programs) &&
           join(paths->program_dir, base, L"Programs") &&
           join(paths->directory, paths->program_dir, L"MedPredict") &&
           join(paths->executable, paths->directory, L"MedPredict.exe") &&
           join(paths->desktop_link, desktop, L"MedPredict.lnk") &&
           join(paths->start_link, programs, L"MedPredict.lnk");
}

static BOOL make_directory(const wchar_t *path) {
    if (CreateDirectoryW(path, NULL)) return TRUE;
    DWORD attributes = GetFileAttributesW(path);
    return attributes != INVALID_FILE_ATTRIBUTES &&
           (attributes & FILE_ATTRIBUTE_DIRECTORY) &&
           !(attributes & FILE_ATTRIBUTE_REPARSE_POINT);
}

static BOOL make_link(const wchar_t *path, const AppPaths *paths) {
    IShellLinkW *link = NULL;
    IPersistFile *persist = NULL;
    HRESULT hr = CoCreateInstance(&CLSID_ShellLink, NULL, CLSCTX_INPROC_SERVER,
                                 &IID_IShellLinkW, (void **)&link);
    if (FAILED(hr)) return FALSE;
    hr = IShellLinkW_SetPath(link, paths->executable);
    if (SUCCEEDED(hr)) hr = IShellLinkW_SetWorkingDirectory(link, paths->directory);
    if (SUCCEEDED(hr)) hr = IShellLinkW_SetDescription(link, L"MedPredict");
    if (SUCCEEDED(hr)) hr = IShellLinkW_SetIconLocation(link, paths->executable, 0);
    if (SUCCEEDED(hr))
        hr = IShellLinkW_QueryInterface(link, &IID_IPersistFile, (void **)&persist);
    if (SUCCEEDED(hr)) hr = IPersistFile_Save(persist, path, TRUE);
    if (persist) IPersistFile_Release(persist);
    IShellLinkW_Release(link);
    return SUCCEEDED(hr);
}

static void remove_own_link(const wchar_t *path, const wchar_t *target) {
    IShellLinkW *link = NULL;
    IPersistFile *persist = NULL;
    wchar_t actual[CAP] = {0};
    HRESULT hr = CoCreateInstance(&CLSID_ShellLink, NULL, CLSCTX_INPROC_SERVER,
                                 &IID_IShellLinkW, (void **)&link);
    if (FAILED(hr)) return;
    hr = IShellLinkW_QueryInterface(link, &IID_IPersistFile, (void **)&persist);
    if (SUCCEEDED(hr)) hr = IPersistFile_Load(persist, path, STGM_READ);
    if (SUCCEEDED(hr)) hr = IShellLinkW_GetPath(link, actual, CAP, NULL, SLGP_RAWPATH);
    BOOL ours = SUCCEEDED(hr) && _wcsicmp(actual, target) == 0;
    if (persist) IPersistFile_Release(persist);
    IShellLinkW_Release(link);
    if (ours) DeleteFileW(path);
}

static BOOL set_value(HKEY key, const wchar_t *name, const wchar_t *value) {
    return RegSetValueExW(key, name, 0, REG_SZ, (const BYTE *)value,
                        (DWORD)((wcslen(value) + 1) * sizeof(wchar_t))) == ERROR_SUCCESS;
}

static BOOL register_app(const AppPaths *paths) {
    HKEY key;
    if (RegCreateKeyExW(HKEY_CURRENT_USER, uninstall_key, 0, NULL, 0,
                        KEY_SET_VALUE, NULL, &key, NULL) != ERROR_SUCCESS) return FALSE;
    wchar_t command[CAP], display_icon[CAP];
    BOOL ok = SUCCEEDED(StringCchPrintfW(command, CAP, L"\"%ls\" --uninstall", paths->executable)) &&
              SUCCEEDED(StringCchPrintfW(display_icon, CAP, L"%ls,0", paths->executable)) &&
              set_value(key, L"DisplayName", L"MedPredict") &&
              set_value(key, L"DisplayVersion", L"1.1.0") &&
              set_value(key, L"Publisher", L"MedPredict") &&
              set_value(key, L"DisplayIcon", display_icon) &&
              set_value(key, L"InstallLocation", paths->directory) &&
              set_value(key, L"UninstallString", command);
    DWORD one = 1;
    RegSetValueExW(key, L"NoModify", 0, REG_DWORD, (const BYTE *)&one, sizeof(one));
    RegSetValueExW(key, L"NoRepair", 0, REG_DWORD, (const BYTE *)&one, sizeof(one));
    RegCloseKey(key);
    return ok;
}

static void open_workspace(void) {
    const wchar_t *folders[] = {L"ProgramFiles(x86)", L"ProgramFiles", L"LocalAppData"};
    const wchar_t *browsers[] = {L"Microsoft\\Edge\\Application\\msedge.exe",
                                L"Google\\Chrome\\Application\\chrome.exe"};
    wchar_t base[CAP], path[CAP], args[CAP];
    StringCchPrintfW(args, CAP, L"--app=\"%ls\"", app_url);
    for (size_t browser = 0; browser < ARRAYSIZE(browsers); ++browser) {
        for (size_t folder = 0; folder < ARRAYSIZE(folders); ++folder) {
            DWORD len = GetEnvironmentVariableW(folders[folder], base, CAP);
            if (!len || len >= CAP || !join(path, base, browsers[browser])) continue;
            DWORD attr = GetFileAttributesW(path);
            if (attr == INVALID_FILE_ATTRIBUTES || (attr & FILE_ATTRIBUTE_DIRECTORY)) continue;
            if ((INT_PTR)ShellExecuteW(NULL, L"open", path, args, NULL, SW_SHOWNORMAL) > 32) return;
        }
    }
    if ((INT_PTR)ShellExecuteW(NULL, L"open", app_url, NULL, NULL, SW_SHOWNORMAL) <= 32)
        MessageBoxW(NULL, L"MedPredict could not open a browser. Install Microsoft Edge or Google Chrome and try again.",
                    L"MedPredict", MB_OK | MB_ICONERROR);
}

static BOOL install_app(const wchar_t *self, const AppPaths *paths) {
    DWORD target = GetFileAttributesW(paths->executable);
    if (target != INVALID_FILE_ATTRIBUTES &&
        (target & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT))) {
        MessageBoxW(NULL, L"The MedPredict installation path is not a regular file.",
                    L"MedPredict", MB_OK | MB_ICONERROR);
        return FALSE;
    }
    if (!make_directory(paths->program_dir) || !make_directory(paths->directory) ||
        !CopyFileW(self, paths->executable, FALSE)) {
        MessageBoxW(NULL, L"MedPredict could not copy the application. Close any running installation and try again.",
                    L"MedPredict", MB_OK | MB_ICONERROR);
        return FALSE;
    }
    BOOL start = make_link(paths->start_link, paths);
    BOOL desktop = make_link(paths->desktop_link, paths);
    BOOL registered = register_app(paths);
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);
    if (!(start && desktop && registered)) {
        MessageBoxW(NULL, L"MedPredict was copied, but Windows could not register all the installation shortcuts. You can run this file again to retry.",
                    L"MedPredict", MB_OK | MB_ICONWARNING);
    }
    return TRUE;
}

/* Run removal from a temporary copy so Windows can release the installed EXE. */
static int begin_uninstall(const wchar_t *self) {
    int choice = MessageBoxW(NULL, L"Remove the installed MedPredict application and its shortcuts?",
                             L"Uninstall MedPredict", MB_YESNO | MB_ICONQUESTION);
    if (choice != IDYES) return 0;
    wchar_t directory[CAP], reservation[CAP], temporary[CAP], command[CAP];
    DWORD n = GetTempPathW(CAP, directory);
    if (!n || n >= CAP || !GetTempFileNameW(directory, L"MDP", 0, reservation)) goto error;
    if (FAILED(StringCchPrintfW(temporary, CAP, L"%ls.exe", reservation)) ||
        !MoveFileW(reservation, temporary)) {
        DeleteFileW(reservation);
        goto error;
    }
    if (!CopyFileW(self, temporary, FALSE)) {
        DeleteFileW(temporary);
        goto error;
    }
    if (FAILED(StringCchPrintfW(command, CAP, L"\"%ls\" --finish-uninstall %lu",
                                temporary, (unsigned long)GetCurrentProcessId()))) {
        DeleteFileW(temporary);
        goto error;
    }
    STARTUPINFOW startup = {0};
    PROCESS_INFORMATION process = {0};
    startup.cb = sizeof(startup);
    if (!CreateProcessW(temporary, command, NULL, NULL, FALSE, 0, NULL, NULL, &startup, &process)) {
        DeleteFileW(temporary);
        goto error;
    }
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return 0;
error:
    MessageBoxW(NULL, L"Could not start removal. Try uninstalling MedPredict again.",
                L"MedPredict", MB_OK | MB_ICONERROR);
    return 1;
}

static int finish_uninstall(const wchar_t *self, const AppPaths *paths, DWORD parent_pid) {
    HANDLE parent = OpenProcess(SYNCHRONIZE, FALSE, parent_pid);
    if (parent) {
        DWORD ready = WaitForSingleObject(parent, 15000);
        CloseHandle(parent);
        if (ready != WAIT_OBJECT_0) return 1;
    }
    if (!DeleteFileW(paths->executable) && GetLastError() != ERROR_FILE_NOT_FOUND) {
        MessageBoxW(NULL, L"Could not remove MedPredict. Close the application and try again.",
                    L"MedPredict", MB_OK | MB_ICONERROR);
        return 1;
    }
    remove_own_link(paths->desktop_link, paths->executable);
    remove_own_link(paths->start_link, paths->executable);
    RegDeleteKeyW(HKEY_CURRENT_USER, uninstall_key);
    RemoveDirectoryW(paths->directory);
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);
    MoveFileExW(self, NULL, MOVEFILE_DELAY_UNTIL_REBOOT);
    MessageBoxW(NULL, L"MedPredict has been removed.", L"MedPredict", MB_OK | MB_ICONINFORMATION);
    return 0;
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR arguments, int show) {
    (void)instance; (void)previous; (void)arguments; (void)show;
    wchar_t self[CAP];
    DWORD length = GetModuleFileNameW(NULL, self, CAP);
    if (!length || length >= CAP) return 1;
    HRESULT com = CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
    if (FAILED(com)) return 1;
    AppPaths paths;
    if (!app_paths(&paths)) {
        MessageBoxW(NULL, L"Windows could not locate your application folders.", L"MedPredict", MB_OK | MB_ICONERROR);
        CoUninitialize();
        return 1;
    }
    int count = 0, result = 0;
    wchar_t **argv = CommandLineToArgvW(GetCommandLineW(), &count);
    BOOL installed = _wcsicmp(self, paths.executable) == 0;
    if (argv && count == 2 && wcscmp(argv[1], L"--uninstall") == 0) {
        if (installed) result = begin_uninstall(self);
    } else if (argv && count == 3 && wcscmp(argv[1], L"--finish-uninstall") == 0) {
        if (!installed) result = finish_uninstall(self, &paths, wcstoul(argv[2], NULL, 10));
    } else {
        if (!installed) {
            int choice = MessageBoxW(NULL,
                L"Install MedPredict? Windows will add MedPredict to your desktop and Start menu. Choose No to open it without installing.",
                L"MedPredict", MB_YESNOCANCEL | MB_ICONQUESTION);
            if (choice == IDCANCEL) goto done;
            if (choice == IDYES && !install_app(self, &paths)) {
                result = 1;
                goto done;
            }
        }
        open_workspace();
    }
done:
    if (argv) LocalFree(argv);
    CoUninitialize();
    return result;
}
