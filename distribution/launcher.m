#import <AppKit/AppKit.h>
#import <fcntl.h>
#import <sys/stat.h>
#import <unistd.h>

static NSString *ShellQuote(NSString *value) {
 return [NSString stringWithFormat:@"'%@'", [value stringByReplacingOccurrencesOfString:@"'" withString:@"'\\''"]];
}

static NSURL *PrepareSetupCommand(NSString *setup, NSString *work, NSError **error) {
 NSString *path=[NSTemporaryDirectory() stringByAppendingPathComponent:[NSString stringWithFormat:@"googlebook-%@.command",NSUUID.UUID.UUIDString]];
 NSString *command=[NSString stringWithFormat:@"#!/bin/bash\nset -euo pipefail\n/bin/rm -- \"$0\"\nexec %@ %@\n",ShellQuote(setup),ShellQuote(work)];
 NSData *data=[command dataUsingEncoding:NSUTF8StringEncoding];
 int fd=open(path.fileSystemRepresentation,O_WRONLY|O_CREAT|O_EXCL,0700);
 if(fd<0) { if(error)*error=[NSError errorWithDomain:NSPOSIXErrorDomain code:errno userInfo:nil];return nil; }
 const char *bytes=data.bytes;NSUInteger remaining=data.length;
 while(remaining) {
  ssize_t count=write(fd,bytes,remaining);
  if(count<0 && errno==EINTR)continue;
  if(count<=0) { int failure=errno;close(fd);unlink(path.fileSystemRepresentation);if(error)*error=[NSError errorWithDomain:NSPOSIXErrorDomain code:failure userInfo:nil];return nil; }
  remaining-=count;bytes+=count;
 }
 close(fd);
 return [NSURL fileURLWithPath:path];
}

static NSString *WorkDirectory(void) {
 NSString *override=NSProcessInfo.processInfo.environment[@"GOOGLEBOOK_WORK"];
 return [(override.length ? override : [NSHomeDirectory() stringByAppendingPathComponent:@".local/share/try-googlebook-os/work"]) stringByStandardizingPath];
}

static BOOL RuntimeReady(NSString *work) {
 NSFileManager *fm=NSFileManager.defaultManager;
 for(NSString *path in @[@"host/Googlebook VM.app/Contents/MacOS/GooglebookViewer",@"host/qemu-interop",@"host/qemu-aarch64-softmmu",@"host/libvirglrenderer.1.dylib",@"host/virgl_render_server",@"image/googlebook.raw",@"image/kernel.Image",@"image/initrd.img",@"UTM-beta/UTM.app/Contents/Frameworks"])
  if(![fm fileExistsAtPath:[work stringByAppendingPathComponent:path]])return NO;
 return YES;
}

@interface Launcher : NSObject<NSApplicationDelegate>
@end
@implementation Launcher
- (void)applicationDidFinishLaunching:(NSNotification *)notification {
 NSString *work=WorkDirectory();
 NSString *app=[work stringByAppendingPathComponent:@"host/Googlebook VM.app"];
 if(RuntimeReady(work)) {
  NSWorkspaceOpenConfiguration *config=NSWorkspaceOpenConfiguration.configuration;
  config.allowsRunningApplicationSubstitution=NO;
  [NSWorkspace.sharedWorkspace openApplicationAtURL:[NSURL fileURLWithPath:app] configuration:config completionHandler:^(NSRunningApplication *running, NSError *error) {
   dispatch_async(dispatch_get_main_queue(),^{
    if(error) { NSAlert *alert=[NSAlert new];alert.messageText=@"Could not open Googlebook VM";alert.informativeText=error.localizedDescription;[alert runModal]; }
    [NSApp terminate:nil];
   });
  }];
  return;
 }
 NSAlert *alert=[NSAlert new];
 alert.messageText=@"Prepare Googlebook OS";
 alert.informativeText=@"This experimental release builds the VM on your Mac. Setup downloads about 9 GB from Google and upstream projects and needs 60 GB free, Homebrew and Xcode command line tools.\n\nTerminal will show progress and ask before installing missing dependencies or accepting Android SDK licences. Your Mac is not repartitioned. USB, real Bluetooth and camera support are not enabled in this alpha.";
 [alert addButtonWithTitle:@"Open setup in Terminal"];
 [alert addButtonWithTitle:@"Cancel"];
 if([alert runModal]==NSAlertFirstButtonReturn) {
  NSURL *script=[NSBundle.mainBundle URLForResource:@"Setup" withExtension:@"command"];
  NSURL *terminal=[NSWorkspace.sharedWorkspace URLForApplicationWithBundleIdentifier:@"com.apple.Terminal"];
  if(!script || !terminal) { NSAlert *failure=[NSAlert new];failure.messageText=@"Setup could not start";failure.informativeText=@"Terminal or the bundled Setup.command is missing. Reinstall this app from its GitHub release.";[failure runModal];[NSApp terminate:nil];return; }
  NSError *prepareError=nil;
  NSURL *handoff=PrepareSetupCommand(script.path,work,&prepareError);
  if(!handoff) { NSAlert *failure=[NSAlert new];failure.messageText=@"Setup could not start";failure.informativeText=prepareError.localizedDescription;[failure runModal];[NSApp terminate:nil];return; }
  [NSWorkspace.sharedWorkspace openURLs:@[handoff] withApplicationAtURL:terminal configuration:NSWorkspaceOpenConfiguration.configuration completionHandler:^(NSRunningApplication *running, NSError *error) {
   dispatch_async(dispatch_get_main_queue(),^{
    if(error) { [NSFileManager.defaultManager removeItemAtURL:handoff error:nil];NSAlert *failure=[NSAlert new];failure.messageText=@"Setup could not start";failure.informativeText=error.localizedDescription;[failure runModal]; }
    [NSApp terminate:nil];
   });
  }];
 } else [NSApp terminate:nil];
}
@end

int main(int argc, char **argv) { @autoreleasepool {
 if(argc==2 && !strcmp(argv[1],"--version")) { NSString *version=[NSBundle.mainBundle objectForInfoDictionaryKey:@"TryGooglebookVersion"] ?: @"development";puts(version.UTF8String);return 0; }
 if(argc==2 && !strcmp(argv[1],"--check")) {
  NSDictionary *status=@{@"ready":@(RuntimeReady(WorkDirectory())),@"work":WorkDirectory()};
  NSData *json=[NSJSONSerialization dataWithJSONObject:status options:0 error:nil];
  fwrite(json.bytes,1,json.length,stdout);putchar('\n');return 0;
 }
 [NSApplication sharedApplication];
 [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
 Launcher *delegate=[Launcher new];NSApp.delegate=delegate;
 [NSApp run];return 0;
}}
