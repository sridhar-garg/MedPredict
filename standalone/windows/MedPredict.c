// A self-contained application: resources and inference are inside this EXE.
// HTTP only serves a fixed, read-only bundle on the local device.
#define WIN32_LEAN_AND_MEAN
#define UNICODE
#define _UNICODE
#include <winsock2.h>
#include <windows.h>
#include <shellapi.h>
#include <shlobj.h>
#include <strsafe.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "bundle.h"

static const wchar_t *url=L"http://127.0.0.1:8766/";
static SOCKET listener=INVALID_SOCKET;
static HINSTANCE module;
static HANDLE server_thread;
static HBRUSH background;

static int send_bytes(SOCKET sock,const void *buf,size_t length){
    const char *p=(const char*)buf;
    while(length){int size=(int)(length>65536?65536:length);int n=send(sock,p,size,0);if(n<=0)return 0;p+=n;length-=n;}
    return 1;
}
static void reply(SOCKET s,int status,const char *reason,const char *mime,const void *body,size_t len){
    char header[1024];
    int n=snprintf(header,sizeof(header),"HTTP/1.1 %d %s\r\nContent-Type: %s\r\nContent-Length: %zu\r\nConnection: close\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nReferrer-Policy: no-referrer\r\nX-Frame-Options: SAMEORIGIN\r\n\r\n",status,reason,mime,len);
    if(n>0&&n<(int)sizeof(header)&&send_bytes(s,header,n))send_bytes(s,body,len);
}
static void serve_one(SOCKET s){
    char req[8192]={0},path[1024],method[12],version[16];int k=0;
    // Bound both request size and receive time. No filesystem or state mutation.
    DWORD timeout=2500;setsockopt(s,SOL_SOCKET,SO_RCVTIMEO,(const char*)&timeout,sizeof(timeout));setsockopt(s,SOL_SOCKET,SO_SNDTIMEO,(const char*)&timeout,sizeof(timeout));
    while(k<(int)sizeof(req)-1&&!strstr(req,"\r\n\r\n")){int n=recv(s,req+k,sizeof(req)-1-k,0);if(n<=0)return;k+=n;req[k]=0;}
    if(!strstr(req,"\r\n\r\n")||sscanf(req,"%11s %1023s %15s",method,path,version)!=3||strcmp(method,"GET")){
        reply(s,400,"Bad Request","text/plain","",0);return;
    }
    // Exact Host check also prevents DNS rebinding to the local resource server.
    char *h=strstr(req,"\r\n");int hosts=0,good=0;
    while(h&&h[2]&&h[2]!='\r'){
        h+=2;char *end=strstr(h,"\r\n");if(!end)break;
        if(_strnicmp(h,"Host:",5)==0){hosts++;char *v=h+5;while(*v==' '||*v=='\t')v++;good=(end-v==14&&memcmp(v,"127.0.0.1:8766",14)==0);}
        h=end;
    }
    if(hosts!=1||!good){reply(s,403,"Forbidden","text/plain","",0);return;}
    char *q=strchr(path,'?');if(q)*q=0;
    if(strcmp(path,"/")==0||strcmp(path,"/auth/callback")==0)strcpy(path,"/index.html");
    for(unsigned i=0;i<sizeof(bundle)/sizeof(bundle[0]);i++){
        if(strcmp(path,bundle[i].path))continue;
        HRSRC resource=FindResourceW(module,MAKEINTRESOURCEW(bundle[i].id),RT_RCDATA);
        if(!resource)break;
        HGLOBAL data=LoadResource(module,resource);
        if(!data)break;
        reply(s,200,"OK",bundle[i].mime,LockResource(data),SizeofResource(module,resource));return;
    }
    reply(s,404,"Not Found","text/plain","",0);
}
static DWORD WINAPI worker(LPVOID unused){
    (void)unused;
    for(;;){
        SOCKET client=accept(listener,NULL,NULL);
        if(client==INVALID_SOCKET)break;
        serve_one(client);shutdown(client,SD_BOTH);closesocket(client);
    }return 0;
}
static int start_server(){
    WSADATA w;if(WSAStartup(MAKEWORD(2,2),&w))return 0;
    listener=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);if(listener==INVALID_SOCKET)return 0;
    BOOL yes=TRUE;if(setsockopt(listener,SOL_SOCKET,SO_EXCLUSIVEADDRUSE,(char*)&yes,sizeof(yes)))return 0;
    struct sockaddr_in a={0};a.sin_family=AF_INET;a.sin_port=htons(8766);a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    if(bind(listener,(struct sockaddr*)&a,sizeof(a))||listen(listener,16))return 0;
    server_thread=CreateThread(NULL,0,worker,NULL,0,NULL);return server_thread!=NULL;
}
static void open_workspace(){
    const wchar_t *folders[]={L"ProgramFiles(x86)",L"ProgramFiles",L"LocalAppData"};
    const wchar_t *browsers[]={L"Google\\Chrome\\Application\\chrome.exe",L"Microsoft\\Edge\\Application\\msedge.exe"};
    wchar_t base[1024],path[1024],args[256];
    StringCchPrintfW(args,256,L"--app=\"%ls\"",url);
    for(unsigned i=0;i<2;i++)for(unsigned j=0;j<3;j++){
        DWORD len=GetEnvironmentVariableW(folders[j],base,1024);
        if(!len||len>=1024)continue;
        if(FAILED(StringCchPrintfW(path,1024,L"%ls\\%ls",base,browsers[i])))continue;
        DWORD attr=GetFileAttributesW(path);
        if(attr==INVALID_FILE_ATTRIBUTES||(attr&FILE_ATTRIBUTE_DIRECTORY))continue;
        if((INT_PTR)ShellExecuteW(NULL,L"open",path,args,NULL,SW_SHOWNORMAL)>32)return;
    }
    if((INT_PTR)ShellExecuteW(NULL,L"open",url,NULL,NULL,SW_SHOWNORMAL)<=32)
        MessageBoxW(NULL,L"Open http://127.0.0.1:8766 in your browser to use AI Workspace.",L"AI Workspace",MB_OK);
}
static LRESULT CALLBACK wndproc(HWND wnd,UINT message,WPARAM w,LPARAM l){
    switch(message){
        case WM_CREATE:{
            HFONT font=(HFONT)GetStockObject(DEFAULT_GUI_FONT);
            HWND a=CreateWindowW(L"STATIC",L"AI Workspace is running on this device.\r\nKeep this window open while using the workspace.",WS_CHILD|WS_VISIBLE,20,18,370,55,wnd,NULL,module,NULL);
            HWND b=CreateWindowW(L"BUTTON",L"Open AI Workspace",WS_CHILD|WS_VISIBLE|BS_DEFPUSHBUTTON,20,80,170,38,wnd,(HMENU)1,module,NULL);
            HWND c=CreateWindowW(L"BUTTON",L"Exit AI Workspace",WS_CHILD|WS_VISIBLE,205,80,170,38,wnd,(HMENU)2,module,NULL);
            SendMessageW(a,WM_SETFONT,(WPARAM)font,TRUE);SendMessageW(b,WM_SETFONT,(WPARAM)font,TRUE);SendMessageW(c,WM_SETFONT,(WPARAM)font,TRUE);return 0;
        }
        case WM_COMMAND:if(LOWORD(w)==1)open_workspace();else if(LOWORD(w)==2)DestroyWindow(wnd);return 0;
        case WM_DESTROY:PostQuitMessage(0);return 0;
    }return DefWindowProcW(wnd,message,w,l);
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE prev,PWSTR command,int show){
    (void)prev;(void)command;(void)show;module=instance;
    HANDLE lock=CreateMutexW(NULL,TRUE,L"Local\\AIWorkspaceStandalone-v2");
    if(!lock)return 1;
    if(GetLastError()==ERROR_ALREADY_EXISTS){HWND old=FindWindowW(L"AIWorkspaceStandaloneWindow",NULL);if(old){ShowWindow(old,SW_RESTORE);SetForegroundWindow(old);}CloseHandle(lock);return 0;}
    if(!start_server()){
        MessageBoxW(NULL,L"AI Workspace could not reserve its private local port. Close any other instance and retry.",L"AI Workspace",MB_OK|MB_ICONERROR);
        if(listener!=INVALID_SOCKET)closesocket(listener);WSACleanup();CloseHandle(lock);return 1;
    }
    WNDCLASSW cls={0};cls.lpfnWndProc=wndproc;cls.hInstance=instance;cls.lpszClassName=L"AIWorkspaceStandaloneWindow";cls.hIcon=LoadIconW(instance,MAKEINTRESOURCEW(1));cls.hCursor=LoadCursorW(NULL,IDC_ARROW);cls.hbrBackground=(HBRUSH)(COLOR_WINDOW+1);
    RegisterClassW(&cls);
    HWND wnd=CreateWindowW(cls.lpszClassName,L"AI Workspace",WS_OVERLAPPED|WS_CAPTION|WS_SYSMENU|WS_MINIMIZEBOX,CW_USEDEFAULT,CW_USEDEFAULT,425,182,NULL,NULL,instance,NULL);
    if(!wnd)return 1;
    ShowWindow(wnd,SW_SHOWMINIMIZED);
    open_workspace();
    MSG msg;while(GetMessageW(&msg,NULL,0,0)>0){TranslateMessage(&msg);DispatchMessageW(&msg);}
    closesocket(listener);WaitForSingleObject(server_thread,3500);CloseHandle(server_thread);WSACleanup();CloseHandle(lock);return 0;
}
