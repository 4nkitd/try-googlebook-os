#define main LauncherMain
#import "../distribution/launcher.m"
#undef main

int main(void) { @autoreleasepool {
 NSFileManager *fm=NSFileManager.defaultManager;
 NSString *root=[NSTemporaryDirectory() stringByAppendingPathComponent:[@"launcher-test-" stringByAppendingString:NSUUID.UUID.UUIDString]];
 NSCAssert([fm createDirectoryAtPath:root withIntermediateDirectories:YES attributes:@{NSFilePosixPermissions:@0700} error:nil],@"Create isolated fixture");
 NSString *setup=[root stringByAppendingPathComponent:@"setup ' quoted.command"];
 NSString *capture=[root stringByAppendingPathComponent:@"arguments.txt"];
 NSString *work=[root stringByAppendingPathComponent:@"chosen ' work $HOME"];
 NSData *stub=[@"#!/bin/bash\nprintf '%s' \"$1\" > \"$CAPTURE_FILE\"\n" dataUsingEncoding:NSUTF8StringEncoding];
 NSCAssert([fm createFileAtPath:setup contents:stub attributes:@{NSFilePosixPermissions:@0700}],@"Create test setup");
 NSError *error=nil;
 NSURL *handoff=PrepareSetupCommand(setup,work,&error);
 NSCAssert(handoff!=nil,@"Generate handoff: %@",error);
 NSDictionary *attributes=[fm attributesOfItemAtPath:handoff.path error:nil];
 NSCAssert([attributes[NSFilePosixPermissions] unsignedIntValue]==0700,@"Private executable handoff");
 NSTask *task=[NSTask new];task.executableURL=[NSURL fileURLWithPath:@"/bin/bash"];task.arguments=@[handoff.path];
 task.environment=@{@"PATH":@"/usr/bin:/bin",@"GOOGLEBOOK_WORK":@"/different-terminal-environment",@"CAPTURE_FILE":capture};
 NSCAssert([task launchAndReturnError:&error],@"Run handoff: %@",error);[task waitUntilExit];
 NSCAssert(task.terminationStatus==0,@"Handoff exit");
 NSString *received=[NSString stringWithContentsOfFile:capture encoding:NSUTF8StringEncoding error:nil];
 NSCAssert([received isEqualToString:work],@"Resolved work directory is preserved verbatim");
 NSCAssert(![fm fileExistsAtPath:handoff.path],@"Temporary handoff removed itself");
 NSCAssert([fm removeItemAtPath:root error:nil],@"Remove isolated fixture");
 puts("PASS: native-to-shell handoff preserves explicit work path despite Terminal environment; quoting and private permissions verified");
 return 0;
}}
